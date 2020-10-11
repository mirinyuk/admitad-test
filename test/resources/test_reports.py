import pytest
import datetime as dt

from flask.testing import FlaskClient
from api.resources.reports import HttpPostData
from api.models.models import ReportTicket
from appfactory import db


@pytest.fixture
def inject_post_request_data() -> HttpPostData:
    return HttpPostData(
        service_domain='ours.com',
        start_from_date=dt.datetime.now(),
        until=dt.datetime.now(),
        recalculate_if_exists=False
    )


def test_post(inject_test_client, inject_post_request_data):
    client: FlaskClient = inject_test_client
    data: HttpPostData = inject_post_request_data

    response = client.post('/api/tickets', data=data.to_json_string(), content_type='application/json')
    assert response.status_code == 200

    # no exception should be thrown from there
    ticket: ReportTicket = ReportTicket.from_dict(response.json)

    # if we already have matching ticket, it should be returned instead of creation of a new one
    response = client.post('/api/tickets', data=data.to_json_string(), content_type='application/json')
    assert ticket.id == ReportTicket.from_dict(response.json).id

    # but if we want exactly new report for whatever reason, no one could prevent us for doing it
    data.recalculate_if_exists = True
    response = client.post('/api/tickets', data=data.to_json_string(), content_type='application/json')
    assert ticket.id != ReportTicket.from_dict(response.json).id

    data.service_domain = None
    assert client.post('/api/tickets', data=data.to_json_string(), content_type='application/json').status_code == 400


def test_get(inject_db_ticket, inject_test_client, inject_app_context):
    ticket: ReportTicket = inject_db_ticket
    client: FlaskClient = inject_test_client

    assert client.get(f'/api/tickets/{ticket.id}').status_code == 202
    ticket.is_completed = True
    db.session.commit()

    assert client.get(f'/api/tickets/{ticket.id}').status_code == 200
