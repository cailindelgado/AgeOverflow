from os import environ
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


def create_app(config_overrides=None):
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 2,
        'max_overflow': 0,
    }

    if config_overrides:
        app.config.update(config_overrides)

    from GCAS.models import db
    from GCAS.models.GCAS import Requests, Results
    db.init_app(app)

    with app.app_context():
        db.create_all()
        db.session.commit()

    from GCAS.views.routes import api
    app.register_blueprint(api)

    return app
