import base64

# imports for validation and cli integration
import uuid
from datetime import datetime as dt
from datetime import timezone as tz

from flask import Blueprint, jsonify, request
from rfc3339_validator import validate_rfc3339 as validate_rfc

# db stuff
from sqlalchemy import exists

from GCAS.models import db
from GCAS.models.GCAS import Photos, Requests, Results, Stats

# worker stuff
from GCAS.tasks import eng

# Constants
UUID_VERSION = 4
VALID_STATUS = ["pending", "success", "failed"]
VALID_GENERATIONS = ["silent", "baby_boomers", "x", "y", "z", "alpha"]
VALID_PARAMS = ["limit", "offset", "start", "end", "user_id", "status", "generation"]
VALID_FILTERS = ["limit", "offset"]
ENGINE_COMMAND = ["../engine", "compute", "--input", "-", "--output", "-"]


api = Blueprint("api", __name__, url_prefix="/api/v1")


def validate_uuid(id: str, version: int | None = None) -> bool:
    """Checks if the given UUID is a valid UUID
    Returns: False if invalid, True otherwise
    """
    try:
        if version:
            uuid.UUID(id, version=version)
        else:
            uuid.UUID(id)
        return True
    except ValueError:
        return False


def validate_encoding(photo: str) -> bool:
    """Checks if the encoding of the given photo is base64
    Returns: False if invalid, True otherwise
    """
    try:
        return base64.b64encode(base64.b64decode(photo)).decode("utf-8") == photo
    except Exception:
        return False


def parse_limit_offset(
    limit: str | None, offset: str | None
) -> tuple[int | None, int | None, tuple | None]:
    """
    Takes in request.args.get() and returns a parsed output.
    return is in the format of (limit, offset, error),
    where error is None if limit and offset are parsed correctly without issues
    """
    if limit is not None:  # 0 < limit <= 1000, default is 100.
        try:
            limit = int(limit)
        except ValueError:
            return None, None, error_response("Limit must be an integer", 400)

        if limit <= 0 or limit > 1000:
            return None, None, error_response("Limit must be between 1 and 1000", 400)
    else:
        limit = 100

    if offset is not None:  # 0 <= offset. Default is 0.
        try:
            offset = int(offset)
        except ValueError:
            return None, None, error_response("Offset must be an integer", 400)

        if offset < 0:
            return None, None, error_response("Offset must be positive", 400)
    else:
        offset = 0

    return limit, offset, None


def error_response(msg: str, status: int):
    return jsonify({"error": msg}), status


@api.route("/health")
def health():
    """
    200 - Service healthy,
    500 - Service is not healthy,
    503 - Service is not healthy
    """
    return jsonify({"status": "Service healthy"}), 200


@api.route("/analysis/<string:customer_id>/requests", methods=["GET"])
def get_requests(customer_id):
    """List all requests for a given customer
    Returns: A list of all requests submitted for the given customer with optional
    filters applied
    """
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        for field in request.args:
            if field not in VALID_PARAMS:
                return error_response("Unknown field", 400)

        query = (
            db.session.query(Requests, Results)
            .outerjoin(Results)
            .filter(Requests.customer_id == customer_id)
        )

        limit, offset, error = parse_limit_offset(
            request.args.get("limit"), request.args.get("offset")
        )
        if error is not None:
            return error

        if "start" in request.args:
            start_str = request.args.get("start")
            if not validate_rfc(start_str):
                return error_response("Invalid starting time", 400)

            start = dt.fromisoformat(start_str).astimezone(tz.utc)
            query = query.filter(Requests.created_at >= start)

        if "end" in request.args:
            end_str = request.args.get("end")
            if not validate_rfc(end_str):
                return error_response("Invalid ending time", 400)

            end = dt.fromisoformat(end_str).astimezone(tz.utc)
            query = query.filter(Requests.created_at <= end)

        if "user_id" in request.args:
            user = request.args.get("user_id")
            if not validate_uuid(user):
                return error_response("Invalid user id", 400)

            query = query.filter(Requests.user_id == user)

        if "status" in request.args:
            status = request.args.get("status")
            if status in VALID_STATUS:
                query = query.filter(Requests.status == status)
            else:
                return error_response("Invalid status", 400)

        if "generation" in request.args:
            gen = request.args.get("generation")
            if gen not in VALID_GENERATIONS:
                return error_response("Invalid Generations", 400)

            query = query.filter(Results.primary_generation == gen)

        query = query.order_by(Requests.created_at.desc())
        requests = query.limit(limit).offset(offset).all()

        result = []
        for req_row, res_row in requests:
            result.append(
                {
                    "id": req_row.request_id,
                    "user_id": req_row.user_id,
                    "created_at": req_row.created_at.isoformat(),
                    "updated_at": req_row.updated_at.isoformat(),
                    "status": req_row.status,
                    "results": {
                        "checksum": res_row.checksum if res_row else None,
                        "generations": res_row.generations if res_row else None,
                        "primary_generation": res_row.primary_generation
                        if res_row
                        else None,
                        "age": res_row.age if res_row else None,
                    },
                }
            )

        return jsonify(result), 200

    except:
        return error_response("Unknown error occurred trying to process request", 500)


@api.route("/analysis/<string:customer_id>/requests", methods=["POST"])
def new_request(customer_id):
    """
    Posts a new analysis request, if the customer account does not exist,
    it will be created
    """
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        if "user_id" not in request.json:
            return error_response("User id missing", 400)

        user = request.json.get("user_id")
        if not validate_uuid(user):
            return error_response("Invalid user_id", 400)

        if "urgent" not in request.json:
            return error_response("Missing urgency of request", 400)

        urgent = request.json.get("urgent")

        if "photos" not in request.json:
            return error_response("Photos missing", 400)

        photos = request.json.get("photos")
        if not photos:
            return error_response("Photos must be present", 400)
        for photo in photos:
            if not validate_encoding(photo):
                return error_response("Invalid photo encoding", 400)

        request_id = str(uuid.uuid4())
        req_status = VALID_STATUS[0]
        new_req = Requests(
            request_id=request_id,
            customer_id=customer_id,
            user_id=user,
            status=req_status,
            result_id=None,
            urgent=urgent,
        )
        store = Photos(id=request_id, photos=photos)

        db.session.add(new_req)
        db.session.flush()
        db.session.add(store)
        db.session.flush()
        db.session.commit()

        engine_input = {"id": request_id, "content": photos}

        queue = "eng-urgent" if urgent else "eng-non-urgent"
        eng.send_data.apply_async(args=[ENGINE_COMMAND, engine_input], queue=queue)

        request_row = db.session.get(Requests, request_id)

        out = {
            "id": request_id,
            "user_id": user,
            "created_at": request_row.created_at.isoformat(),
            "updated_at": request_row.updated_at.isoformat(),
            "status": req_status,
            "result": {
                "checksum": None,
                "generations": None,
                "primary_generation": None,
                "age": None,
            },
        }

        return jsonify(out), 201

    except Exception as e:
        print(e)
        return error_response("Unknown error occurred trying to process request", 500)


@api.route(
    "/analysis/<string:customer_id>/requests/<string:request_id>", methods=["GET"]
)
def get_request(customer_id, request_id):
    """Gets the request by the identifier"""
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        if not validate_uuid(request_id):
            return error_response("Invalid request id", 400)

        if not db.session.query(
            exists().where(
                Requests.customer_id == customer_id, Requests.request_id == request_id
            )
        ).scalar():
            return error_response(
                "Request with given customer_id and request_id does not exist", 404
            )

        row = Requests.query.filter_by(
            request_id=request_id, customer_id=customer_id
        ).first()

        if row.status == VALID_STATUS[1]:
            request_result = (
                Results.query.filter_by(result_id=row.result_id).first().to_dict()
            )
        else:
            request_result = {
                "checksum": None,
                "generations": {
                    "silent": None,
                    "baby_boomers": None,
                    "x": None,
                    "y": None,
                    "z": None,
                    "alpha": None,
                },
                "primary_generation": None,
                "age": None,
            }

        result = {
            "id": row.request_id,
            "user_id": row.user_id,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "status": row.status,
            "result": request_result,
        }

        return jsonify(result), 200

    except:
        return error_response("Unknown error occurred trying to process request", 500)


@api.route("/analysis/<string:customer_id>/statistics", methods=["GET"])
def get_statistics(customer_id):
    """Get the statistics for the given customer"""
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        if not db.session.query(
            exists().where(Requests.customer_id == customer_id)
        ).scalar():
            return error_response("Customer id not found", 404)

        out = Stats.query.filter_by(customer_id=customer_id).first()
        return jsonify(out.to_dict()), 200

    except:
        return error_response("Unknown error occurred trying to process request", 500)


@api.route("/analysis/<string:customer_id>/users", methods=["GET"])
def get_users(customer_id):
    """
    Returns an unordered list of all users for the given customer id with optional filters applied
    """
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        if not db.session.query(
            exists().where(Requests.customer_id == customer_id)
        ).scalar():
            return error_response("Unknown customer", 400)

        for field in request.args:
            if field not in VALID_FILTERS:
                return error_response("Unknown query parameter", 400)

        limit, offset, error = parse_limit_offset(
            request.args.get("limit"), request.args.get("offset")
        )
        if error is not None:
            return error

        # Filter to desired customer and remove unwanted columns
        user_rows = (
            db.session.query(Requests.user_id)
            .filter(Requests.customer_id == customer_id)
            .group_by(Requests.user_id)
            .limit(limit)
            .offset(offset)
            .all()
        )

        user_ids = [row.user_id for row in user_rows]
        requests = (
            db.session.query(Requests, Results)
            .where(Requests.user_id.in_(user_ids), Requests.customer_id == customer_id)
            .outerjoin(Results)
            .all()
        )

        users = {}
        for uid in user_ids:  # build based on paginated uids (to keep order)
            users[uid] = []

        # go through each request and add user info
        for req_row, res_row in requests:
            users[req_row.user_id].append(
                {
                    "id": req_row.request_id,
                    "status": req_row.status,
                    "checksum": res_row.checksum if res_row else None,
                    "primary_generation": res_row.primary_generation
                    if res_row
                    else None,
                    "age": res_row.age if res_row else None,
                }
            )

        out = []
        for user, results in users.items():
            out.append({"id": user, "results": results})

        return jsonify(out), 200

    except:
        return error_response("Unknown error occurred trying to process request", 500)


@api.route("/analysis/<string:customer_id>/users/<string:user_id>", methods=["GET"])
def get_user(customer_id, user_id):
    """Get all requests associated with a user."""
    try:
        if not validate_uuid(customer_id, UUID_VERSION):
            return error_response("Invalid customer id", 400)

        if not validate_uuid(user_id):
            return error_response("Invalid user id", 400)

        # Ensure that customer_id and request_id exist
        if not db.session.query(
            exists().where(
                Requests.customer_id == customer_id, Requests.user_id == user_id
            )
        ).scalar():
            return error_response(
                "Request with given customer_id and user_id does not exist", 404
            )

        query = db.session.query(Requests, Results).filter(
            Requests.customer_id == customer_id, Requests.user_id == user_id
        )
        requests = query.outerjoin(Results).all()

        results = []
        for req_row, res_row in requests:
            if res_row is None:
                results.append(
                    {
                        "id": req_row.request_id,
                        "status": req_row.status,
                        "checksum": None,
                        "primary_generation": None,
                        "age": None,
                    }
                )
            else:
                results.append(res_row.user_to_dict(req_row.request_id, req_row.status))

        return jsonify({"id": user_id, "results": results}), 200

    except:
        return error_response("Unknown error occurred trying to process request", 500)
