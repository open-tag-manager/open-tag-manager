from retriever_base import RetrieverBase
from urllib.parse import urlparse
import pandas as pd
import json
import time
import argparse
import uuid
import datetime
import os
import boto3
from decimal import Decimal


class DataRetriever(RetrieverBase):
    def __init__(self, **kwargs):
        super(DataRetriever, self).__init__(**kwargs)

    @staticmethod
    def _normalizeUrl(url):
        if isinstance(url, str):
            if url and url.lower() == 'undefined':
                return url

            if url:
                parsedurl = urlparse(url)
                return "{0}://{1}{2}".format(parsedurl.scheme, parsedurl.netloc, parsedurl.path)

        return None

    def execute(self):
        self.make_partition()

        stime = datetime.datetime.utcfromtimestamp(int(self.options['query_stime'] / 1000))
        etime = datetime.datetime.utcfromtimestamp(int(self.options['query_etime'] / 1000))

        q = ''
        q += " org = '%s'" % self.options['query_org']
        q += " AND tid = '%s'" % self.options['query_tid']
        q += ' AND year * 10000 + month * 100 + day >= %s' % stime.strftime('%Y%m%d')
        q += ' AND year * 10000 + month * 100 + day <= %s' % etime.strftime('%Y%m%d')
        q += " AND datetime >= timestamp '%s'" % (stime.strftime('%Y-%m-%d %H:%M:%S'))
        q += " AND datetime <= timestamp '%s'" % (etime.strftime('%Y-%m-%d %H:%M:%S'))
        q += " AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL"

        sql = """SELECT 
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
FROM {0}.{1}
WHERE {2}
GROUP BY 
JSON_EXTRACT_SCALAR(qs, '$.dl'), 
JSON_EXTRACT_SCALAR(qs, '$.o_pl'),
JSON_EXTRACT_SCALAR(qs, '$.dt'),
JSON_EXTRACT_SCALAR(qs, '$.o_s'),
JSON_EXTRACT_SCALAR(qs, '$.o_ps'),
JSON_EXTRACT_SCALAR(qs, '$.el'),
JSON_EXTRACT_SCALAR(qs, '$.o_a_id')
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        self._save_usage_report(self.options['target_bucket'], self.options['query_org'], self.options['query_tid'],
                                result_athena)

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        urls = []
        url_links_map = {}
        result = []
        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            result.append(event)
            url = self._normalizeUrl(event['url'])
            p_url = self._normalizeUrl(event['p_url'])
            if url and url not in urls:
                urls.append(url)
            if p_url and p_url not in urls:
                urls.append(p_url)

        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            url = self._normalizeUrl(event['url'])
            p_url = self._normalizeUrl(event['p_url'])
            key = "{0}-{1}".format(url, p_url)
            if key in url_links_map:
                url_links_map[key]['count'] += event['count']
            else:
                url_links_map[key] = {'count': event['count'], 'url': url, 'p_url': p_url,
                                      'title': event['title']}

        url_links = []
        for key in url_links_map:
            url_links.append(url_links_map[key])

        sql2 = """WITH scroll as (
SELECT 
datet, url, p_url, COUNT(y) as s_count, SUM(CAST(y as decimal)) as sum_scroll_y, MAX(CAST(y as decimal)) as max_scroll_y
FROM 
(
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
MAX(JSON_EXTRACT_SCALAR(qs, '$.o_e_y')) as y,
JSON_EXTRACT_SCALAR(qs, '$.cid') as uid
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'scroll_%' AND {2}
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
FROM {0}.{1}
WHERE {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl') 
),

widget_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(datetime) as w_click_count
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_widget_%' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl')
),

trivial_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
COUNT(datetime) as t_click_count
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_trivial_%' AND {2}
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
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview'
AND CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal) > 0 
AND CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal) <= 30000 
AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl')
)

SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datetime,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
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
{0}.{1}
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
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_pl'),s_count, sum_scroll_y, max_scroll_y, event_count, w_click_count, t_click_count, plt_count, sum_plt, max_plt
ORDER BY count DESC
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql2)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        self._save_usage_report(self.options['target_bucket'], self.options['query_org'], self.options['query_tid'],
                                result_athena)

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        target = self.s3.Object(self.options['target_bucket'], self.options['target_name'])
        target_raw = self.s3.Object(self.options['target_bucket'], self.options['target_name_raw'])

        table_result = []
        for index, row in pd_data.iterrows():
            url = self._normalizeUrl(row['url'])
            p_url = self._normalizeUrl(row['p_url'])
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

        sql3 = """SELECT 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS url,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS title,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.el') AS label,
COUNT(*) as count
FROM {0}.{1}
WHERE {2}
GROUP BY 
JSON_EXTRACT_SCALAR(qs, '$.dl'), 
JSON_EXTRACT_SCALAR(qs, '$.dt'),
JSON_EXTRACT_SCALAR(qs, '$.o_s'),
JSON_EXTRACT_SCALAR(qs, '$.el')
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql3)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        event_table_result = []
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        for index, row in pd_data.iterrows():
            event = json.loads(row.to_json())
            url = self._normalizeUrl(event['url'])
            r = [d for d in event_table_result if d['url'] == url and d['state'] == event['state']]
            if r:
                r[0]['count'] += event['count']
            else:
                event['url'] = url
                event_table_result.append(event)

        print(json.dumps({'message': 'dump data',
                          'bucket': 's3://' + self.options['target_bucket'] + '/' + self.options['target_name']}))
        print(json.dumps(result))
        print(json.dumps(table_result))

        target.put(Body=json.dumps({
            'meta': {
                'stime': self.options['query_stime'],
                'etime': self.options['query_etime'],
                'tid': self.options['query_tid'],
                'version': 3,
                'type': 'summary'
            },
            'urls': urls,
            'url_links': url_links,
            'table': table_result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')
        target_raw.put(Body=json.dumps({
            'meta': {
                'stime': self.options['query_stime'],
                'etime': self.options['query_etime'],
                'tid': self.options['query_tid'],
                'version': 3,
                'type': 'raw'
            },
            'result': result,
            'event_table': event_table_result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')


def main():
    parser = argparse.ArgumentParser(description='Make stats from Athena')
    parser.add_argument('--query-org', dest='query_org', required=True, help='organization name')
    parser.add_argument('--query-tid', dest='query_tid', required=True, help='tid (Container Name)')
    parser.add_argument('--query-stime', dest='query_stime', type=int, required=True,
                        help='Query start time (msec unix time)')
    parser.add_argument('--query-etime', dest='query_etime', type=int, required=True,
                        help='Query end time (msec unix time)')
    parser.add_argument('--file-key', dest='file_key', required=True, help='File key')
    args = vars(parser.parse_args())

    dynamodb = boto3.resource('dynamodb')
    stat_table = dynamodb.Table(str(os.environ.get('OTM_STAT_DYNAMODB_TABLE')))
    queue_record_key = {'tid': args['query_org'] + '/' + args['query_tid'], 'timestamp': Decimal(args['file_key'])}

    queue_record = stat_table.get_item(Key=queue_record_key)

    if 'Item' not in queue_record:
        print('Queue data not found')
        return

    if not queue_record['Item']['status'] == 'QUEUED':
        print('Queue data is not QUEUED status')

    stat_table.update_item(Key=queue_record_key, UpdateExpression='set #s = :s', ExpressionAttributeValues={
        ':s': 'IN_PROGRESS'
    }, ExpressionAttributeNames={
        '#s': 'status'
    })

    o_prefix = ''
    if args['query_org'] != 'root':
        o_prefix = args['query_org'] + '/'

    args['target_bucket'] = os.environ.get('OTM_STATS_BUCKET')
    args['target_prefix'] = (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + args['query_tid'] + '/'
    args['target_prefix_raw'] = (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + args['query_tid'] + '_raw/'
    args['usage_prefix'] = (os.environ.get('OTM_USAGE_PREFIX') or '')
    args['athena_result_bucket'] = os.environ.get('STATS_ATHENA_RESULT_BUCKET')
    args['athena_result_prefix'] = os.environ.get('STATS_ATHENA_RESULT_PREFIX') or ''
    args['athena_database'] = os.environ.get('STATS_ATHENA_DATABASE')
    args['athena_table'] = os.environ.get('STATS_ATHENA_TABLE')

    target_name = time.strftime("%Y%m%d%H%M%S") + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_stime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_etime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    target_name += str(uuid.uuid4())
    args['target_name'] = args['target_prefix'] + target_name + '.json'
    args['target_name_raw'] = args['target_prefix_raw'] + target_name + '.json'

    retriever = DataRetriever(**args)
    retriever.execute()

    stat_table.update_item(
        Key=queue_record_key,
        UpdateExpression='set #s = :s, file_key = :f, raw_file_key = :r',
        ExpressionAttributeValues={
            ':s': 'COMPLETE',
            ':f': args['target_name'],
            ':r': args['target_name_raw']
        },
        ExpressionAttributeNames={
            '#s': 'status'
        }
    )


if __name__ == '__main__':
    main()
