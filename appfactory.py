from os import getenv
from importlib import import_module

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_dramatiq import Dramatiq
from flask_cors import CORS

from config import DevFlaskConfig, TestFlaskConfig, ProdFlaskConfig, IMPORTS


ENV = getenv('FLASK_ENV', 'dev')
CONFIGURATIONS = {
    'dev': DevFlaskConfig, 'test': TestFlaskConfig, 'prod': ProdFlaskConfig
}


db = SQLAlchemy()
ma = Marshmallow()
dramatiq = Dramatiq()
cors = CORS()


def create_app() -> Flask:

    for module in IMPORTS:
        import_module(name=module)

    app = Flask(__name__)
    app.config.from_object(CONFIGURATIONS[ENV])

    db.init_app(app)
    ma.init_app(app)
    dramatiq.init_app(app)
    cors.init_app(app=app, resources={'/api/*': {"origins": "*"}})

    from api.blueprint import api_bp
    app.register_blueprint(api_bp)

    return app
