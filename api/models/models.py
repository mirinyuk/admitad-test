from typing import *

from marshmallow import fields, post_load
from sqlalchemy.dialects.postgresql import JSONB

from appfactory import db, ma
from config import FlaskConfig


class LogRecord(db.Model):
    __tablename__ = 'referrals_log'
    __table_args__ = {'schema': FlaskConfig.DB_SCHEMA_NAME}

    id = db.Column(db.Integer, primary_key=True)
    record = db.Column(JSONB, nullable=False)


class WinnersReportEntry(db.Model):
    __tablename__ = 'winners_report'
    __table_args__ = {'schema': FlaskConfig.DB_SCHEMA_NAME}

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey(f'{FlaskConfig.DB_SCHEMA_NAME}.reports_tickets.id'),
        nullable=False
    )
    user_id = db.Column(db.String, nullable=False)
    winner = db.Column(db.String, nullable=False)

    class Schema(ma.Schema):
        user_id = fields.String()
        winner = fields.String()

    _serializer = Schema()

    def as_dict(self) -> Dict[str, str]:
        return self._serializer.dump(self)


class ReportTicket(db.Model):
    __tablename__ = 'reports_tickets'
    __table_args__ = {'schema': FlaskConfig.DB_SCHEMA_NAME}

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime, server_default=db.text("now()"))

    service_domain = db.Column(db.String(128), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)

    is_completed = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text('false'))

    report_entries: List[WinnersReportEntry] = db.relationship(
        WinnersReportEntry, cascade="all, delete-orphan")

    class Schema(ma.Schema):
        id = fields.Integer()
        service_domain = fields.String()
        period_start = fields.Date()
        period_end = fields.Date()
        created_time = fields.DateTime()
        is_completed = fields.Boolean()
        report_entries = fields.List(fields.Nested(WinnersReportEntry.Schema))

        @post_load
        def make_obj(self, data: Dict, **kw):
            return ReportTicket(**data)

    _serializer = Schema()

    def as_dict(self) -> Dict[str, Union[str, int]]:
        return self._serializer.dump(self)

    @classmethod
    def from_dict(cls, data: Dict, **kw):
        return cls._serializer.load(data)
