from . import db
from datetime import datetime as dt, timezone as tz
from sqlalchemy.dialects.postgresql import JSONB, UUID

# Imports for event driven approach for statistics
from sqlalchemy.dialects.postgresql import insert as pg_insert, ARRAY
from sqlalchemy import event, select, update, func, case, cast
from sqlalchemy.types import Integer, Text

# Constants
MAX_STATUS_LENGTH = 7
MAX_PRIMARY_LENGTH = 11  # longest option is baby_boomers -> 11 chars
# Checksum hash is compressed then encoded in hex, 32 chars should be enough
CHECKSUM_LENGTH = 32

# const for stochastic formula
ETA = 0.01


class Photos(db.Model):
    # Schema: photos[id, photos]
    __tablename__ = 'photos'

    id = db.Column(UUID(as_uuid=False), db.ForeignKey(
        'requests.request_id'), nullable=False, primary_key=True)
    photos = db.Column(JSONB, nullable=False)

    def to_dict(self):
        return {
            'request_id': self.id,
            'photos': self.photos
        }


class Requests(db.Model):
    # Schema: requests[request_id, customer_id, user_id, status, created_at, updated_at, result_id, urgent]
    __tablename__ = 'requests'

    request_id = db.Column(UUID(as_uuid=False), primary_key=True)
    customer_id = db.Column(UUID(as_uuid=False), nullable=False, index=True)
    user_id = db.Column(UUID(as_uuid=False), nullable=False, index=True)
    status = db.Column(db.String(MAX_STATUS_LENGTH),
                       nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True),
                           nullable=False, default=lambda: dt.now(tz.utc))
    updated_at = db.Column(db.DateTime(timezone=True),
                           nullable=False, default=lambda: dt.now(tz.utc))
    result_id = db.Column(db.BigInteger, db.ForeignKey(
        'results.result_id'), nullable=True)
    urgent = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            'request_id': self.request_id,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'result_id': self.result_id,
            'urgent': self.urgent,
        }

    def __repr__(self):
        return f'<Requests: {self.request_id}>'


class Results(db.Model):
    # Schema: results[result_id, checksum, generations, primary_generation, age]
    __tablename__ = 'results'

    result_id = db.Column(db.BigInteger, primary_key=True)
    checksum = db.Column(db.String(CHECKSUM_LENGTH), nullable=False)
    generations = db.Column(JSONB, nullable=False)
    primary_generation = db.Column(
        db.String(MAX_PRIMARY_LENGTH), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'checksum': self.checksum,
            'generations': self.generations,
            'primary_generation': self.primary_generation,
            'age': self.age,
        }

    def user_to_dict(self, request_id: str, status: str):
        return {
            'id': request_id,
            'status': status,
            'checksum': self.checksum,
            'primary_generation': self.primary_generation,
            'age': self.age,
        }

    def __repr__(self):
        return f'<Results: {self.result_id}>'


# """ Event driven statistics calculations for benchmarking in stage 3
class Stats(db.Model):
    # Schema: statistics[customer_id, total_users, total_requests, mean, median, buckets]
    __tablename__ = 'stats'
    bucket_default = {'20': 0, '30': 0, '40': 0,
                      '50': 0, '60': 0, '70': 0, '80': 0}

    customer_id = db.Column(UUID(as_uuid=False), primary_key=True)
    total_users = db.Column(db.Integer, nullable=False, default=0)
    total_requests = db.Column(db.Integer, nullable=False, default=0)
    mean = db.Column(db.Float, nullable=False, default=0.0)
    median = db.Column(db.Float, nullable=False, default=0.0)
    buckets = db.Column(JSONB, nullable=False, default=bucket_default)

    def to_dict(self):
        return {
            'generated_at': dt.now(tz.utc).isoformat(),
            'contents': {
                'total_users': self.total_users,
                'total_requests': self.total_requests,
                'mean': self.mean,
                'median': self.median,
                'buckets': self.buckets
            }
        }


    # Event listeners and helpers
    @event.listens_for(Requests, 'after_insert')
    def update_non_age(mapper, connection, target):
        # Update the total users and total requests
        users = connection.execute(
            select(func.count(Requests.user_id))
            .where(Requests.customer_id == target.customer_id,
                   Requests.user_id == target.user_id)
            .group_by(Requests.user_id)
        ).scalar()

        if users > 1:
            users = 0
        stats = Stats.__table__

        # Attempt handling insert with customer_id, defaults SHOULD handle other columns
        new = pg_insert(stats).values(
            customer_id=target.customer_id,
            total_users=users,
            total_requests=1
        )

        # increment request based counters
        connection.execute(new.on_conflict_do_update(
            index_elements=['customer_id'],
            set_={
                'total_users': stats.c.total_users + users,
                'total_requests': stats.c.total_requests + 1,
            }
        )
        )

    @event.listens_for(Requests, 'after_update')
    def update_age(mapper, connection, target):
        # Update the buckets, mean, and median
        if target.result_id is None:
            return

        age = connection.execute(
            select(Results.age)
            .where(Results.result_id == target.result_id)
        ).scalar()

        stats = Stats.__table__
        bucket = '20' if age <= 29 else '80' if 80 <= age else str(
            age - (age % 10))

        # update the existing row (requests always inserted before results)
        connection.execute(
            update(stats)
            .where(stats.c.customer_id == target.customer_id)
            .values(
                mean=case(
                    (stats.c.mean == 0, age),
                    else_=stats.c.mean + (ETA * (age - stats.c.mean))
                ),
                median=case(
                    (stats.c.median == 0, age),
                    else_=stats.c.median + ETA *
                    func.sign(age - stats.c.median)
                ),
                buckets=func.jsonb_set(
                    stats.c.buckets,
                    cast([bucket], ARRAY(Text)),
                    func.to_jsonb(
                        cast(stats.c.buckets[bucket].astext, Integer) + 1)
                )
            )
        )
        # """