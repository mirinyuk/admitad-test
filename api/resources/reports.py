from typing import *
from dataclasses import dataclass
import datetime as dt

from flask import request, abort, current_app
from flask_restful import Resource
from marshmallow import ValidationError, fields, validate, post_load

from appfactory import db, ma
from api.blueprint import api
from api.models.models import ReportTicket
from api.service.winners_report_actor import winners_report_actor


@dataclass
class HttpPostData:
    start_from_date: dt.date
    until: dt.date
    service_domain: str
    recalculate_if_exists: bool = False

    class Schema(ma.Schema):
        start_from_date = fields.Date(required=True, allow_none=False)
        until = fields.Date(required=True, allow_none=False)
        service_domain = fields.String(
            required=True, allow_none=False, validate=validate.OneOf(('ours.com', 'theirs1.com', 'theirs2.com')))
        recalculate_if_exists = fields.Boolean(required=False, allow_none=True)

        @post_load
        def make_obj(self, data, **kw):
            return HttpPostData(**data)

    _serializer = Schema()

    @classmethod
    def from_dict(cls, data: Dict):
        return cls._serializer.load(data)

    def to_json_string(self):
        return self._serializer.dumps(self)


@api.resource(
    '/tickets',
    '/tickets/<int:ticket_id>'
)
class ReportTicketResource(Resource):

    @staticmethod
    def get(ticket_id: Optional[int] = None):
        if not ticket_id:
            abort(403)

        is_completed: bool = db.session.query(ReportTicket.is_completed).filter(ReportTicket.id == ticket_id).scalar()
        if is_completed is None:
            abort(404)

        if is_completed:
            ticket: ReportTicket = ReportTicket.query.get(ticket_id)
            return ticket.as_dict(), 200
        return {'message': 'Not finished yet'}, 202

    def post(self, **kw):
        try:
            http_query: HttpPostData = HttpPostData.from_dict(request.json)
        except ValidationError as e:
            current_app.logger.info(repr(e))
            return {'error': e.messages}, 400

        if http_query.recalculate_if_exists:
            return self.__submit_new_ticket(http_query).as_dict(), 200

        # if there is a calculations with matching parameters, return the last calculated
        try_exists: List[ReportTicket] = ReportTicket.query.filter_by(
            period_start=http_query.start_from_date,
            period_end=http_query.until,
            service_domain=http_query.service_domain
        ).order_by(ReportTicket.created_time.desc()).limit(1).all()

        if try_exists:
            return try_exists.pop().as_dict(), 200

        return self.__submit_new_ticket(http_query).as_dict(), 200

    @staticmethod
    def __submit_new_ticket(http_query: HttpPostData) -> ReportTicket:
        ticket = ReportTicket(
            period_start=http_query.start_from_date,
            period_end=http_query.until,
            service_domain=http_query.service_domain
        )

        db.session.add(ticket)
        db.session.commit()

        winners_report_actor.send(ticket.id)

        current_app.logger.info(f'Submitted new {ticket.id=}')

        return ticket
