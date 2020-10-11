from typing import *
from dataclasses import dataclass
import datetime as dt
import json

from flask import request
from flask_restful import Resource
from marshmallow import fields, ValidationError, post_load

from appfactory import db, ma
from api.blueprint import api
from api.models.models import LogRecord


@dataclass
class ReferralsLogEntry:
    date: dt.datetime
    user_agent: str
    doc_location: str
    doc_referrer: str
    client_id: str

    class Schema(ma.Schema):
        date = fields.DateTime(required=True, allow_none=False)
        user_agent = fields.String(required=True, allow_none=False, data_key='User-Agent')
        doc_location = fields.Url(required=True, allow_none=False, data_key='document.location')
        doc_referrer = fields.Url(required=True, allow_none=False, data_key='document.referer')
        client_id = fields.String(required=True, allow_none=False)

        @post_load
        def make_obj(self, data, **kw):
            return ReferralsLogEntry(**data)

    _serializer = Schema()

    @classmethod
    def to_dict(cls, instance, *other, many: bool = False) -> List[dict]:
        return cls._serializer.dump((instance, *other) if many else instance, many=many)

    @classmethod
    def from_str(cls, data: Union[str, bytes], many: bool = False):
        return cls._serializer.loads(data, many=many)

    @classmethod
    def from_dict(cls, instance: dict, *other: Tuple[dict], many: bool = False):
        return cls._serializer.load((instance, *other) if many else instance, many=many)


@api.resource('/uploader/log')
class LogUploader(Resource):

    @staticmethod
    def post():
        try:
            ReferralsLogEntry.from_dict(*request.json, many=True)
        except ValidationError as e:
            return {'error': e.messages}, 400

        records = [LogRecord(record=item) for item in request.json]
        db.session.bulk_save_objects(records)
        db.session.commit()

        return {'message': 'success'}, 200

    @staticmethod
    def put():
        # supposed to be idempotent, violating here only for testing usability

        if not request.files or len(tuple(request.files)) > 1:
            return {'error': 'No (or more than one) file provided'}, 400

        # also not good to store potentially big files in memory, just for testing purpose
        records_str: bytes = next(iter(request.files.values())).stream.read()

        try:
            ReferralsLogEntry.from_str(records_str, many=True)
        except ValidationError as e:
            return {'error': e.messages}, 400

        records = [LogRecord(record=item) for item in json.loads(records_str)]
        db.session.bulk_save_objects(records)
        db.session.commit()

        return (), 200
