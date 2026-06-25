import os
from subprocess import run
from json import dumps
from celery import Celery
from celery.signals import worker_process_init

import json
from GCAS import create_app
from GCAS.models import db
from GCAS.models.GCAS import Results, Requests
from datetime import datetime as dt, timezone as tz

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL")
celery.conf.task_default_queue = os.environ.get("CELERY_DEFAULT_QUEUE", "celery")

@worker_process_init.connect
def init_worker(**kwargs):
    app = create_app()
    app.app_context().push()

@celery.task(name="eng")
def send_data(command: list[str], input: dict[str, any]):
    engine = run(
        command,
        input=dumps(input),
        capture_output=True,
        text=True
    )

    if engine.returncode:
        req_status = "failed"
        id = None
    else:
        req_status = "success"
        out = json.loads(engine.stdout).get('results')

        result = Results(
            checksum=out.get('checksum'),
            generations=out.get('generations'),
            primary_generation=out.get('primary_generation'),
            age=out.get('age')
        )

        db.session.add(result)
        db.session.flush()
        id = result.result_id
    
    req_row = db.session.get(Requests, input.get('id'))
    req_row.result_id = id
    req_row.status = req_status
    req_row.updated_at = dt.now(tz.utc)
    db.session.commit()
