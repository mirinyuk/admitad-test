create schema admitad authorization admitad;

create table admitad.referrals_log (
    id serial primary key ,
    record jsonb not null
);

create table admitad.reports_tickets (
    id serial primary key ,
    created_time timestamp not null default now(),
    service_domain varchar(256) not null ,
    period_start date not null ,
    period_end date not null ,
    is_completed bool not null
);

create table admitad.winners_report (
    -- we need dummy ids because of SQLAlchemy query logic
    id serial primary key ,
    ticket_id integer not null references admitad.reports_tickets on delete cascade ,
    user_id varchar(512) not null ,
    winner varchar(512) not null
);
