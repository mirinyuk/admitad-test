# Тестовое задание

### Некоторые допущения:

1. Отсутствует пример логов добавления товара в корзину (и удаления из неё), соответственно, 
невозможно установить наличие в ней товара и понять, 
что именно было куплено. Например, в сценарии: "пользователь перешел ссылке, добавил в 
корзину, тут же перешел еще по одной, затем оплатил", не понятно были ли 
оплачены оба товара или только один, или вообще что-то другое, что в корзине уже было. 
Потому считаем, что переход по партнёрской ссылке равнозначен добавлению товара в корзину.
 Для других сценариев недостаточно данных. Пример записи, 
 для которой нельзя установить что было куплено (из задания):
	```json
	{
		"client_id": "user7",
		"User-Agent": "Chrome 65",
		"document.location": "https://shop.com/checkout",
		"document.referer": "https://shop.com/cart",
		"date": "2018-05-23T19:05:59.224000Z"
	}
	```
2. В задании сказано, что данные хранятся в БД, и наиболее подходящей базой для такого 
формата хранения является MongoDB. Однако, из-за отсутствия времени на изучение, была 
выбрана PostgreSQL, у которой есть нативная работа с JSON
3. В задании не указана необходимость формировать отчет за конкретный промежуток времени, 
но это кажется логичным
4. Не известен объем данных. Из расчета на "долгие" запросы, API сделан асинхронным: по 
запросу создаётся тикет, по которому через некоторое время можно получить отчет. Фронт 
может периодично опрашивать API на предмет готовности, это не создаёт блокирующую нагрузку.

### Развёртывание
```bash
docker-compose up
```

### API:

**DTO** (сериализуются в json)
```python
class ReportTicket:
    id = fields.Integer()  
    service_domain = fields.String()  
    period_start = fields.Date()  
    period_end = fields.Date()  
    created_time = fields.DateTime()  
    is_completed = fields.Boolean()  
    report_entries = fields.List(fields.Nested(WinnersReportEntry))
    
class WinnersReportEntry:  
    user_id = fields.String()  
    winner = fields.String()	# "победившая" ссылка
```

**Получить тикет** 
```http request
POST /api/tickets
content-type: application/json
	{
		"start_from_date": "<date_iso_string>",
		"until": "<date_iso_string>",
		"service_domain": "<cashback service domain name>",
		"recalculate_if_exists": <true/flase>
	}
	
RESPONSE:
	HTTP CODE 200
	ReportTicket

ERROR:
	HTTP CODE 400: ошибка валидации
	body: {"message": "<error string>"}
```
**Получить отчет**
```http request
GET /api/tickets/<int:ticket_id>

RESPONSE:
	HTTP CODE 202: отчет еще не сформирован
	HTTP CODE 200, ReportTicket
```
**Загрузить файл лога**
```http request
PUT /api/uploader/log <file>
content-type: multipart/form-data

###

POST /api/uploader/log <JSON>
content-type: application/json
```

### Использование:
После запуска контейнеров по адресу http://localhost:8081 доступна веб-страничка. Фронт 
сделан по принципу "минимально работающее" для удобства тестирования бэка.
Можно загружать логи в БД через форму загрузки файлов. На логах из задания работать 
не будет, тк там есть опечатки (https://shop.com/products/?id=2, 
https://shop.com/products/id?=2). На момент запуска БД пустая. В директории test 
проекта есть тестовый лог файл.

### Подход к решению
Задача сводится к выбору всех "чекаутов" за период, для которых выборка логов "до" по 
данному юзеру, товару и любым партнёрским переходам, отсортированная по убыванию даты 
и ограниченная снизу датой предыдущего "checkout", 
содержит первой строкой переход с указанного в задаче сервиса (тк мы не учитываем 
"органические" переходы и переходы внутри магазина, которые могут случиться "между" 
этими событиями).

### SQL
Задача решается таким запросом:
```sql
with
     ticket as (
        select id as ticket_id, service_domain, period_start, period_end
        from admitad.reports_tickets
        where id = :ticket_id
     ),

     purchases_candidates as (
        select record as purchase,
               lag(record, 1) over (
                   partition by record ->> 'client_id'
                   order by (record ->> 'date')::timestamp desc
               ) as prev_checkout
        from admitad.referrals_log, ticket
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
                   record ->> 'document.location' from '(?<=(?:\\?|&)id=)\d+'
               ) as pid
        from admitad.referrals_log, ticket
        where (record ->> 'date')::date <= period_end and
              record ->> 'document.referer' ~ 'ours.com/|theirs1.com/|theirs2.com/'
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

    insert into admitad.winners_report (ticket_id, user_id, winner)
    select ticket_id,
           purchase ->> 'client_id' as user_id,
           candidate ->> 'document.referer' as winner
    from joined, ticket
    where rnk = 1 and
          candidate ->> 'document.referer' like '%'||service_domain||'%' and
          (candidate ->> 'date')::timestamp > coalesce(prev_checkout_date, 'epoch'::timestamp);
```

### Структура проекта
Бэк реализован на Flask + PostgreSQL. Для асинхронного формирования отчетов 
используется [dramatiq](https://github.com/Bogdanp/dramatiq) и Redis в кач-ве 
брокера сообщений. NginX раздаёт статику (тестовая веб-страничка) и выступает 
reverse proxy для Gunicorn. Воркер **dramatiq** живёт в отдельном контейнере.

### Что можно улучшить
1. Построить индексы
2. Избавиться от регулярных выражений
3. Возможно, перейти на документоориентированную БД или изменить формат хранения данных
