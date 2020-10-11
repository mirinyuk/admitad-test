from os import getenv


IMPORTS = ['api.models', 'api.resources']

CASHBACK_SERVICES_DOMAINS_REGEX = r'ours\.com/', r'theirs1\.com/', r'theirs2\.com/'


class FlaskConfig:
    DB_SCHEMA_NAME = 'admitad'

    TESTING = False
    DEBUG = False

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DRAMATIQ_BROKER = 'dramatiq.brokers.redis:RedisBroker' if getenv('FLASK_ENV') != 'test' \
        else 'dramatiq.brokers.stub:StubBroker'

    # up to 100 Mb
    MAX_BODY_SIZE = 1024**2 * 100


class DevFlaskConfig(FlaskConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_ECHO = True

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://admitad:admitad@localhost:5432/admitad'
    DRAMATIQ_BROKER_URL = 'redis://localhost:6379/0'


class TestFlaskConfig(DevFlaskConfig):
    DRAMATIQ_BROKER_URL = None


class ProdFlaskConfig(FlaskConfig):
    SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{getenv("DB_USER")}:{getenv("DB_PASS")}' \
                              f'@{getenv("DB_ADDR")}:{getenv("DB_PORT")}/{getenv("DB_NAME")}'
    DRAMATIQ_BROKER_URL = getenv('REDIS_URL')
