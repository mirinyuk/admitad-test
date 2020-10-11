from logging import getLogger, Logger
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

from config import CASHBACK_SERVICES_DOMAINS_REGEX, FlaskConfig
from api.models.models import ReportTicket


class CashbackWinnersReportRunner:

    SERVICES_MATCHER = '|'.join(CASHBACK_SERVICES_DOMAINS_REGEX)

    __query_str = f'''
    with
        ticket as (
            select id as ticket_id, service_domain, period_start, period_end
            from {FlaskConfig.DB_SCHEMA_NAME}.reports_tickets
            where id = :ticket_id
         ),

        purchases_candidates as (
            select record as purchase,
                   lag(record, 1) over (
                       partition by record ->> 'client_id'
                       order by (record ->> 'date')::timestamp desc
                   ) as prev_checkout
            from {FlaskConfig.DB_SCHEMA_NAME}.referrals_log, ticket
            where (record ->> 'date')::date <= period_end and
                  record ->> 'document.location' = 'https://shop.com/checkout'
        ),

        purchases as (
             select purchase,
                    (prev_checkout ->> 'date')::timestamp as prev_checkout_date
             from purchases_candidates, ticket
             where (purchase ->> 'date')::timestamp >= period_start
        ),

        candidates as (
            select record as candidate,
                   substring(
                       record ->> 'document.location' from '(?<=shop\\.com/products/?(?:\\?|&)id=)\\d+'
                   ) as pid
            from {FlaskConfig.DB_SCHEMA_NAME}.referrals_log, ticket
            where (record ->> 'date')::date <= period_end and
                  record ->> 'document.referer' ~ :services_matcher
        ),

        joined as (
             select prev_checkout_date,
                    purchase,
                    candidate,
                    row_number() over (
                        partition by candidate ->> 'client_id', candidates.pid
                        order by (candidate ->> 'date')::timestamp desc
                    ) as rnk
             from purchases, candidates, ticket
             where purchase ->> 'client_id' = candidate ->> 'client_id' and
                   candidates.pid is not null and
                   (candidate ->> 'date')::timestamp < (purchase ->> 'date')::timestamp
        )

        insert into {FlaskConfig.DB_SCHEMA_NAME}.winners_report (ticket_id, user_id, winner)
        select ticket_id,
               purchase ->> 'client_id' as user_id,
               candidate ->> 'document.referer' as winner
        from joined, ticket
        where rnk = 1 and
              candidate ->> 'document.referer' like '%'||service_domain||'%' and
              (candidate ->> 'date')::timestamp > coalesce(prev_checkout_date, 'epoch'::timestamp)
    '''

    def __init__(self, db: SQLAlchemy):
        self.logger: Logger = getLogger(f'{self.__class__.__name__}')
        self.db = db
        self._query = db.text(self.__query_str)

    def run_report(self, ticket_id: int):

        query_params = {'ticket_id': ticket_id, 'services_matcher': self.SERVICES_MATCHER}

        self.logger.info(f'Started report {ticket_id=}')
        try:
            self.db.session.execute(self._query, query_params)
        except SQLAlchemyError as e:
            self.logger.exception(e)
            self.db.session.rollback()
            raise RuntimeError('Could not finish transaction') from e
        else:
            ticket: ReportTicket = ReportTicket.query.get(ticket_id)
            ticket.is_completed = True
            self.db.session.commit()
            self.logger.info(f'Finished report {ticket_id=}')
