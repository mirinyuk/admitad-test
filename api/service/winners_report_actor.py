from appfactory import dramatiq, db
from api.service.report_runner import CashbackWinnersReportRunner


@dramatiq.actor(queue_name='winners_report_tasks')
def winners_report_actor(ticket_id: int):
    reporter = CashbackWinnersReportRunner(db)
    reporter.run_report(ticket_id=ticket_id)
