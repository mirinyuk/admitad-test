from api.service.report_runner import CashbackWinnersReportRunner
from appfactory import db


def test_report(inject_app_context, inject_db_ticket):
    reporter = CashbackWinnersReportRunner(db=db)
    reporter.run_report(ticket_id=inject_db_ticket.id)
