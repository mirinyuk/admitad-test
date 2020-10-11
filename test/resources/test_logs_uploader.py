from io import BytesIO
from flask.testing import FlaskClient


def test_post(
        inject_test_client,
        inject_invalid_log_string,
        inject_valid_log_string
):
    client: FlaskClient = inject_test_client

    assert client.post(
        '/api/uploader/log', data=inject_invalid_log_string,
        content_type='application/json').status_code == 400

    assert client.post(
        '/api/uploader/log', data=inject_valid_log_string,
        content_type='application/json').status_code == 200


def test_put(
        inject_test_client,
        inject_invalid_log_string,
        inject_valid_log_string
):
    client: FlaskClient = inject_test_client

    assert client.put('/api/uploader/log',
                      data={'file': (BytesIO(bytes(inject_invalid_log_string, encoding='utf-8')), 'log.json')},
                      content_type='multipart/form-data').status_code == 400
    assert client.put('/api/uploader/log',
                      data={'file': (BytesIO(bytes(inject_valid_log_string, encoding='utf-8')), 'log.json')},
                      content_type='multipart/form-data').status_code == 200
