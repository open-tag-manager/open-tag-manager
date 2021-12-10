from chalice import Blueprint
from . import app, authorizer, s3, s3_client, athena_client, execute_athena_query, save_athena_usage_report
from .decorator import check_org_permission, check_json_body
from urllib.parse import urlparse
import pandas as pd
import os
import json
import datetime

stats_routes = Blueprint(__name__)


def normalize_url(url):
    if isinstance(url, str):
        if url and url.lower() == 'undefined':
            return url

        if url:
            parsedurl = urlparse(url)
            return "{0}://{1}{2}".format(parsedurl.scheme, parsedurl.netloc, parsedurl.path)

    return None


def generate_base_criteria(org, tid, stime, etime):
    q = ''
    q += " org = '%s'" % org
    q += " AND tid = '%s'" % tid
    q += ' AND year * 10000 + month * 100 + day >= %s' % stime.strftime('%Y%m%d')
    q += ' AND year * 10000 + month * 100 + day <= %s' % etime.strftime('%Y%m%d')
    q += " AND datetime >= timestamp '%s'" % (stime.strftime('%Y-%m-%d %H:%M:%S'))
    q += " AND datetime <= timestamp '%s'" % (etime.strftime('%Y-%m-%d %H:%M:%S'))
    q += " AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL"
    return q


def generate_object_name(org, tid, stime, etime, suffix):
    return '%s%s/%s_%s_%s.json' % (
        '' if org == 'root' else org + '/',
        tid,
        stime.strftime('%Y%m%d%H%M%S'),
        etime.strftime('%Y%m%d%H%M%S'),
        suffix
    )


def url_link_query(org, tid, stime, etime):
    return """SELECT 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS title,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.o_ps') AS p_state,
JSON_EXTRACT_SCALAR(qs, '$.el') AS label,
JSON_EXTRACT_SCALAR(qs, '$.o_a_id') AS a_id,
arbitrary(JSON_EXTRACT_SCALAR(qs, '$.o_xpath')) AS xpath,
arbitrary(JSON_EXTRACT_SCALAR(qs, '$.o_a_class')) AS class,
COUNT(*) as count
FROM {0}
WHERE {1}
GROUP BY 
JSON_EXTRACT_SCALAR(qs, '$.dl'), 
JSON_EXTRACT_SCALAR(qs, '$.o_pl'),
JSON_EXTRACT_SCALAR(qs, '$.dt'),
JSON_EXTRACT_SCALAR(qs, '$.o_s'),
JSON_EXTRACT_SCALAR(qs, '$.o_ps'),
JSON_EXTRACT_SCALAR(qs, '$.el'),
JSON_EXTRACT_SCALAR(qs, '$.o_a_id')
""".format(os.environ.get('STATS_ATHENA_TABLE'), generate_base_criteria(org, tid, stime, etime))


@stats_routes.route('/start_query_url_links', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_stats_start_query_url_links(org, name):
    request = app.current_request
    body = request.json_body
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    execution_id = execute_athena_query(url_link_query(org, name, stime, etime), token='url_links')

    return {'execution_id': execution_id}


@stats_routes.route('/query_result_url_links', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'execution_id': {'type': 'string', 'required': True},
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_query_result_url_links(org, name):
    request = app.current_request
    body = request.json_body
    execution_id = body['execution_id']
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id,
    )

    file_url_url_links = None
    file_url_event_graph = None

    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    if state == 'SUCCEEDED':
        result_data = s3.Bucket(os.environ.get('STATS_ATHENA_RESULT_BUCKET')).Object('%s.csv' % (execution_id)).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        urls = []
        url_links_map = {}
        result = []
        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            result.append(event)
            url = normalize_url(event['url'])
            p_url = normalize_url(event['p_url'])
            if url and url not in urls:
                urls.append(url)
            if p_url and p_url not in urls:
                urls.append(p_url)

        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            url = normalize_url(event['url'])
            p_url = normalize_url(event['p_url'])
            key = "{0}-{1}".format(url, p_url)
            if key in url_links_map:
                url_links_map[key]['count'] += event['count']
            else:
                url_links_map[key] = {'count': event['count'], 'url': url, 'p_url': p_url,
                                      'title': event['title']}

        url_links = []
        for key in url_links_map:
            url_links.append(url_links_map[key])

        target = s3.Object(os.environ.get('OTM_STATS_BUCKET'), generate_object_name(org, name, stime, etime, 'url_links'))
        target.put(Body=json.dumps({
            'meta': {
                'stime': int(stime.timestamp() * 1000),
                'etime': int(etime.timestamp() * 1000),
                'tid': name,
                'version': 4,
                'type': 'url_links'
            },
            'urls': urls,
            'url_links': url_links
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        file_url_url_links = s3_client.generate_presigned_url('get_object', {'Key': target.key, 'Bucket': target.bucket_name})

        target_graph = s3.Object(os.environ.get('OTM_STATS_BUCKET'), generate_object_name(org, name, stime, etime, 'event_graph'))
        target_graph.put(Body=json.dumps({
            'meta': {
                'stime': int(stime.timestamp() * 1000),
                'etime': int(etime.timestamp() * 1000),
                'tid': name,
                'version': 4,
                'type': 'event_graph'
            },
            'data': result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        file_url_event_graph = s3_client.generate_presigned_url('get_object', {'Key': target.key, 'Bucket': target.bucket_name})
        save_athena_usage_report(org, name, state_result)

    return {
        'state': state,
        'file_url_links': file_url_url_links,
        'file_event_graph': file_url_event_graph
    }


def url_table_query(org, tid, stime, etime):
    return """
WITH 
title as (
SELECT
datet, url, FIRST_VALUE(title) OVER (PARTITION BY url ORDER BY datet) as title
FROM
(
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.dt') as title
FROM {0}
WHERE {1}
) tmp
),

scroll as (
SELECT 
datet, url, p_url, COUNT(y) as s_count, SUM(CAST(y as decimal)) as sum_scroll_y, MAX(CAST(y as decimal)) as max_scroll_y
FROM 
(
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
MAX(JSON_EXTRACT_SCALAR(qs, '$.o_e_y')) as y,
JSON_EXTRACT_SCALAR(qs, '$.cid') as cid
FROM {0}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'scroll_%' AND {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl'), JSON_EXTRACT_SCALAR(qs, '$.cid')
) tmp 
GROUP BY datet, url, p_url
),

event as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(datetime) as event_count
FROM {0}
WHERE {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl') 
),

widget_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(datetime) as w_click_count
FROM {0}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_widget_%' AND {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl')
),

trivial_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(datetime) as t_click_count
FROM {0}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_trivial_%' AND {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl')
),

plt as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(JSON_EXTRACT_SCALAR(qs, '$.plt')) as plt_count,
SUM(CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal)) as sum_plt,
MAX(CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal)) as max_plt
FROM {0}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview'
AND CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal) > 0 
AND CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal) <= 30000 
AND {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl')
)

SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datetime,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
title.title,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(qs) as count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.o_psid')) as session_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as user_count,
scroll.s_count,
scroll.sum_scroll_y,
scroll.max_scroll_y,
event.event_count,
widget_click.w_click_count,
trivial_click.t_click_count,
plt.plt_count,
plt.sum_plt,
plt.max_plt
FROM 
{0}
LEFT OUTER JOIN
title ON (title.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND title.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
scroll ON (scroll.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND scroll.p_url = JSON_EXTRACT_SCALAR(qs, '$.o_pl') AND scroll.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
event ON (event.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND event.p_url = JSON_EXTRACT_SCALAR(qs, '$.o_pl') AND event.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
widget_click ON (widget_click.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND widget_click.p_url = JSON_EXTRACT_SCALAR(qs, '$.o_pl') AND widget_click.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
trivial_click ON (trivial_click.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND trivial_click.p_url = JSON_EXTRACT_SCALAR(qs, '$.o_pl') AND trivial_click.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN
plt ON (plt.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND plt.p_url = JSON_EXTRACT_SCALAR(qs, '$.o_pl') AND plt.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview' AND {1}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), 
JSON_EXTRACT_SCALAR(qs, '$.dl'),
JSON_EXTRACT_SCALAR(qs, '$.o_pl'),
title,
s_count, sum_scroll_y, max_scroll_y, event_count, w_click_count, t_click_count, plt_count, sum_plt, max_plt
ORDER BY count DESC
""".format(os.environ.get('STATS_ATHENA_TABLE'), generate_base_criteria(org, tid, stime, etime))


def pageview_time_series(org, tid, stime, etime):
    return """
WITH
date_range as (SELECT 
  FORMAT_DATETIME(dt, 'Y-MM-dd') as date
FROM (SELECT 1)
CROSS JOIN UNNEST(
  sequence(
    CAST('{0}' AS date),
    CAST('{1}' AS date),
    INTERVAL '1' DAY
  )
) AS t(dt)),
pageview AS (
  SELECT FORMAT_DATETIME(datetime, 'Y-MM-dd') as date, JSON_EXTRACT_SCALAR(qs, '$.o_psid') as psid, JSON_EXTRACT_SCALAR(qs, '$.cid') as cid 
  FROM {2}
  WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview' 
  AND {3}
),

daily AS (SELECT dr.date as date, 
COUNT(pageview.date) as pageview_count,
COUNT(DISTINCT pageview.psid) as session_count,
COUNT(DISTINCT pageview.cid) as user_count
FROM 
date_range dr
LEFT OUTER JOIN pageview ON (pageview.date = dr.date)
GROUP BY dr.date
)

SELECT
*
FROM (
SELECT
date,
pageview_count,
SUM(pageview_count) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as pageview_count_3days,
SUM(pageview_count) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as pageview_count_7days,
SUM(pageview_count) OVER (ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as pageview_count_14days,
SUM(pageview_count) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as pageview_count_30days,
session_count,
SUM(session_count) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as session_count_3days,
SUM(session_count) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as session_count_7days,
SUM(session_count) OVER (ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as session_count_14days,
SUM(session_count) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as session_count_30days,
user_count,
SUM(user_count) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as user_count_3days,
SUM(user_count) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as user_count_7days,
SUM(user_count) OVER (ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as user_count_14days,
SUM(user_count) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as user_count_30days
FROM
daily
) 
WHERE date >= '{4}'
ORDER BY date ASC
""".format(
        (stime - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
        etime.strftime('%Y-%m-%d'),
        os.environ.get('STATS_ATHENA_TABLE'),
        generate_base_criteria(org, tid, (stime - datetime.timedelta(days=30)), etime),
        stime.strftime('%Y-%m-%d')
    )


@stats_routes.route('/start_query_pageview_time_series', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_stats_start_pageview_time_series(org, name):
    request = app.current_request
    body = request.json_body
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)


    q = pageview_time_series(org, name, stime, etime)
    execution_id = execute_athena_query(q, token='pageview_time_series')

    return {'execution_id': execution_id}


@stats_routes.route('/query_result_pageview_time_series', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'execution_id': {'type': 'string', 'required': True},
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_query_result_pageview_time_series(org, name):
    request = app.current_request
    body = request.json_body
    execution_id = body['execution_id']
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id,
    )
    file = None
    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    if state == 'SUCCEEDED':
        result_data = s3.Bucket(os.environ.get('STATS_ATHENA_RESULT_BUCKET')).Object('%s.csv' % (execution_id)).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        result = []

        for index, row in pd_data.iterrows():
            result.append(json.loads(row.to_json()))

        target = s3.Object(os.environ.get('OTM_STATS_BUCKET'), generate_object_name(org, name, stime, etime, 'pageview_time_series'))
        target.put(Body=json.dumps({
            'meta': {
                'stime': int(stime.timestamp() * 1000),
                'etime': int(etime.timestamp() * 1000),
                'tid': name,
                'version': 4,
                'type': 'pageview_time_series'
            },
            'table': result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        file = s3_client.generate_presigned_url('get_object', {'Key': target.key, 'Bucket': target.bucket_name})
        save_athena_usage_report(org, name, state_result)

    return {
        'state': state,
        'file': file
    }


@stats_routes.route('/start_query_url_table', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_stats_start_query_url_table(org, name):
    request = app.current_request
    body = request.json_body
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    execution_id = execute_athena_query(url_table_query(org, name, stime, etime), token='url_table')

    return {'execution_id': execution_id}


@stats_routes.route('/query_result_url_table', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'execution_id': {'type': 'string', 'required': True},
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_query_result_url_table(org, name):
    request = app.current_request
    body = request.json_body
    execution_id = body['execution_id']
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id,
    )
    file = None
    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    if state == 'SUCCEEDED':
        result_data = s3.Bucket(os.environ.get('STATS_ATHENA_RESULT_BUCKET')).Object('%s.csv' % (execution_id)).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        table_result = []

        for index, row in pd_data.iterrows():
            url = normalize_url(row['url'])
            p_url = normalize_url(row['p_url'])

            rj = json.loads(row.to_json())

            r = [d for d in table_result if d['url'] == url and d['p_url'] == p_url and d['datetime'] == rj['datetime']]
            if len(r) > 0:
                # merge data
                r[0]['count'] += rj['count'] or 0
                r[0]['session_count'] += rj['session_count'] or 0
                r[0]['user_count'] += rj['user_count'] or 0
                r[0]['s_count'] += rj['s_count'] or 0
                r[0]['sum_scroll_y'] += rj['sum_scroll_y'] or 0
                r[0]['max_scroll_y'] = max(r[0]['max_scroll_y'], rj['max_scroll_y'] or 0)
                r[0]['event_count'] += rj['event_count'] or 0
                r[0]['w_click_count'] += rj['w_click_count'] or 0
                r[0]['t_click_count'] += rj['t_click_count'] or 0
                r[0]['plt_count'] += rj['plt_count'] or 0
                r[0]['sum_plt'] += rj['sum_plt'] or 0
                r[0]['max_plt'] += rj['max_plt'] or 0
            else:
                # initialize data
                rj['url'] = url
                rj['p_url'] = p_url
                rj['title'] = rj['title']
                rj['count'] = rj['count'] or 0
                rj['session_count'] = rj['session_count'] or 0
                rj['user_count'] = rj['user_count'] or 0
                rj['s_count'] = rj['s_count'] or 0
                rj['sum_scroll_y'] = rj['sum_scroll_y'] or 0
                rj['max_scroll_y'] = rj['max_scroll_y'] or 0
                rj['event_count'] = rj['event_count'] or 0
                rj['w_click_count'] = rj['w_click_count'] or 0
                rj['t_click_count'] = rj['t_click_count'] or 0
                rj['plt_count'] = rj['plt_count'] or 0
                rj['sum_plt'] = rj['sum_plt'] or 0
                rj['max_plt'] = rj['max_plt'] or 0
                table_result.append(rj)

        for t_result in table_result:
            if t_result['s_count'] and t_result['s_count'] > 0:
                t_result['avg_scroll_y'] = t_result['sum_scroll_y'] / t_result['s_count']
            else:
                t_result['avg_scroll_y'] = None

            if t_result['plt_count'] and t_result['plt_count'] > 0:
                t_result['avg_plt'] = t_result['sum_plt'] / t_result['plt_count']
            else:
                t_result['avg_plt'] = None

        target = s3.Object(os.environ.get('OTM_STATS_BUCKET'), generate_object_name(org, name, stime, etime, 'url_table'))
        target.put(Body=json.dumps({
            'meta': {
                'stime': int(stime.timestamp() * 1000),
                'etime': int(etime.timestamp() * 1000),
                'tid': name,
                'version': 4,
                'type': 'url_table'
            },
            'table': table_result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        file = s3_client.generate_presigned_url('get_object', {'Key': target.key, 'Bucket': target.bucket_name})
        save_athena_usage_report(org, name, state_result)

    return {
        'state': state,
        'file': file
    }


def event_table_query(org, name, stime, etime):
    return """SELECT 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS url,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS title,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.el') AS label,
COUNT(*) as count
FROM {0}
WHERE {1}
GROUP BY 
JSON_EXTRACT_SCALAR(qs, '$.dl'), 
JSON_EXTRACT_SCALAR(qs, '$.dt'),
JSON_EXTRACT_SCALAR(qs, '$.o_s'),
JSON_EXTRACT_SCALAR(qs, '$.el')
""".format(os.environ.get('STATS_ATHENA_TABLE'), generate_base_criteria(org, name, stime, etime))


@stats_routes.route('/start_query_event_table', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_stats_start_query_event_table(org, name):
    request = app.current_request
    body = request.json_body
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    execution_id = execute_athena_query(event_table_query(org, name, stime, etime), token='event_table')

    return {'execution_id': execution_id}


@stats_routes.route('/query_result_event_table', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    'execution_id': {'type': 'string', 'required': True},
    'stime': {'type': 'integer', 'required': True},
    'etime': {'type': 'integer', 'required': True}
})
def make_container_query_result_event_table(org, name):
    request = app.current_request
    body = request.json_body
    execution_id = body['execution_id']
    stime = datetime.datetime.utcfromtimestamp(int(body['stime']) / 1000)
    etime = datetime.datetime.utcfromtimestamp(int(body['etime']) / 1000)

    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id,
    )
    file = None
    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    if state == 'SUCCEEDED':
        result_data = s3.Bucket(os.environ.get('STATS_ATHENA_RESULT_BUCKET')).Object('%s.csv' % (execution_id)).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        event_table_result = []

        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            url = normalize_url(event['url'])
            r = [d for d in event_table_result if d['url'] == url and d['state'] == event['state']]
            if r:
                r[0]['count'] += event['count']
            else:
                event['url'] = url
                event_table_result.append(event)

        target = s3.Object(os.environ.get('OTM_STATS_BUCKET'), generate_object_name(org, name, stime, etime, 'event_table'))
        target.put(Body=json.dumps({
            'meta': {
                'stime': int(stime.timestamp() * 1000),
                'etime': int(etime.timestamp() * 1000),
                'tid': name,
                'version': 4,
                'type': 'event_table'
            },
            'table': event_table_result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        file = s3_client.generate_presigned_url('get_object', {'Key': target.key, 'Bucket': target.bucket_name})
        save_athena_usage_report(org, name, state_result)

    return {
        'state': state,
        'file': file
    }
