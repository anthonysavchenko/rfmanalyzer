from django.db import connection


def write_to_sheet(sheet, query_result):
    columns = ('Телефон', 'Клиент', 'Недель с первой покупки',
               'Недель с последней покупки', 'Недель с покупками',
               'Покупок на сумму', 'Частота покупок', 'Категория')

    [sheet.write(0, index, column) for index, column in enumerate(columns)]

    [[sheet.write(row_index + 1, column_index, row[column_index])
        for column_index in range(len(columns))]
     for row_index, row in enumerate(query_result)]


def execute_query(since, till, user_id):
    with connection.cursor() as cursor:
        query = _get_query(since, till, user_id)
        cursor.execute(query)
        return tuple(row for row in cursor.fetchall())


def _get_query(since_monday, till_monday, user_id):
    return f" \
        SELECT \
            t1.phone, \
            t1.customer_name, \
            t1.weeks_since_first_pay, \
            t1.weeks_since_last_pay, \
            t1.payed_weeks, \
            t1.payed_total, \
            ROUND( \
                CAST( \
                    (t1.weeks_since_first_pay - t1.weeks_since_last_pay) \
                        AS REAL) / (payed_weeks - 1), 2) AS ntc, \
            CASE \
                WHEN \
                    payed_weeks <= 1 \
                THEN \
                    '5 - Unknown' \
                WHEN \
                    t1.weeks_since_last_pay > ROUND(CAST( \
                        (t1.weeks_since_first_pay - t1.weeks_since_last_pay) \
                            AS REAL) / (payed_weeks - 1), 2) * 3 \
                THEN \
                    '4 - Black' \
                WHEN \
                    t1.weeks_since_last_pay > ROUND(CAST( \
                        (t1.weeks_since_first_pay - t1.weeks_since_last_pay) \
                            AS REAL) / (payed_weeks - 1), 2) * 2 \
                THEN \
                    '1 - Red' \
                WHEN \
                    t1.weeks_since_last_pay > ROUND(CAST( \
                        (t1.weeks_since_first_pay - t1.weeks_since_last_pay) \
                            AS REAL) / (payed_weeks - 1), 2) \
                THEN \
                    '2 - Yellow' \
                ELSE \
                    '3 - Green' \
            END AS sector \
        FROM \
            (SELECT \
                c.id AS customer_id, \
                CONCAT( \
                    '+', \
                    SUBSTR(c.phone, 1, 1), \
                    ' (', \
                    SUBSTR(c.phone, 2, 3), \
                    ') ', \
                    SUBSTR(c.phone, 5, 3), \
                    '-', \
                    SUBSTR(c.phone, 8, 2), \
                    '-', \
                    SUBSTR(c.phone, 10, 2)) AS Phone, \
                c.customer_name AS customer_name, \
                CAST( \
                    (TO_DAYS('{till_monday:%Y-%m-%d}') - \
                        TO_DAYS(MAX(w.since))) / 7 \
                    AS UNSIGNED) AS weeks_since_last_pay, \
                CAST( \
                    (TO_DAYS('{till_monday:%Y-%m-%d}') - \
                        TO_DAYS(MIN(w.since))) / 7 \
                    AS UNSIGNED) AS weeks_since_first_pay, \
                COUNT(w.id) AS payed_weeks, \
                SUM(w.payed) AS payed_total \
            FROM \
                analysis_customer AS c \
            JOIN \
                analysis_week AS w \
            ON \
                c.id = w.customer_id AND \
                c.user_id = {user_id} AND \
                w.since BETWEEN '{since_monday:%Y-%m-%d}' AND \
                    '{till_monday:%Y-%m-%d}' \
            GROUP BY \
                c.id, \
                c.customer_name, \
                c.phone) AS t1 \
        ORDER BY \
            sector, \
            payed_total DESC;\
    "
