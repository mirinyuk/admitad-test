import pytest
import json
from pathlib import Path
import datetime as dt

from flask import Flask
from flask.testing import FlaskClient
from dramatiq import Worker, Broker

from appfactory import create_app, db, dramatiq
from api.models.models import ReportTicket


@pytest.fixture
def inject_app_context():
    app = create_app()
    with app.app_context():
        yield


@pytest.fixture
def inject_app() -> Flask:
    return create_app()


@pytest.fixture()
def inject_stub_worker() -> Worker:
    worker = Worker(dramatiq.broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture
def inject_stub_broker() -> Broker:
    broker: Broker = dramatiq.broker
    broker.flush_all()
    return broker


@pytest.fixture
def inject_test_client(inject_app) -> FlaskClient:
    app: Flask = inject_app
    with app.test_client() as client:
        yield client


@pytest.fixture
def inject_invalid_log_string() -> str:
    log = [
        {
            "client_id": "user15",
            "User-Agent": "Firefox 59",
            "document.location": "!invalid",
            "document.referer": "https://yandex.ru/search/?q=купить+котика",
            "date": "2018-04-03T07:59:13.286000Z"
        },
        {
            "client_id": "user15",
            "User-Agent": "Firefox 59",
            "document.location": "https://shop.com/products/id?=2",
            "document.referer": "invalid",
            "date": "2018-04-04T08:30:14.104000Z"
        },
    ]
    return json.dumps(log)


@pytest.fixture
def inject_valid_log_string() -> str:
    with Path.cwd().joinpath('test_log_data.json').open('r') as f:
        return f.read()


@pytest.fixture
def inject_db_ticket(inject_app_context) -> ReportTicket:
    ticket: ReportTicket = ReportTicket(
        period_start=dt.datetime(year=1900, month=1, day=1).date(),
        period_end=dt.datetime.now().date(),
        service_domain='ours.com'
    )

    db.session.add(ticket)
    db.session.commit()

    yield ticket

    ticket = ReportTicket.query.get(ticket.id)

    db.session.delete(ticket)
    db.session.commit()
