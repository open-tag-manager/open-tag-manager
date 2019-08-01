from retrying import retry
from urllib.parse import urlparse
import pandas as pd
import json
import time
import boto3
import argparse
import uuid
import datetime


class DataRetriever:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.s3 = boto3.resource('s3')
        self.athena = boto3.client('athena')

    @retry(stop_max_attempt_number=10,
           wait_exponential_multiplier=1000,
           wait_exponential_max=10 * 60 * 1000)
    def _poll_status(self, id):
        print(json.dumps({'message': 'poll status', 'id': id}))
        result = self.athena.get_query_execution(
            QueryExecutionId=id
        )
        state = result['QueryExecution']['Status']['State']
        if state == 'SUCCEEDED':
            return result
        elif state == 'FAILED':
            return result
        else:
            raise Exception

    @staticmethod
    def _normalizeUrl(url):
        if url and url.lower() == 'undefined':
            return url

        if url:
            parsedurl = urlparse(url)
            return "{0}://{1}{2}".format(parsedurl.scheme, parsedurl.netloc, parsedurl.path)

        return None

    def _execute_athena_query(self, query):
        print(json.dumps({'message': 'execute athena', 'query': query}))
        response = self.athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={
                'OutputLocation': 's3://%s/%s' % (
                    self.options['athena_result_bucket'], self.options['athena_result_prefix']),
                'EncryptionConfiguration': {
                    'EncryptionOption': 'SSE_S3'
                }
            }
        )
        QueryExecutionId = response['QueryExecutionId']
        return self._poll_status(QueryExecutionId)

    def execute(self):
        result = self._execute_athena_query(
            'MSCK REPAIR TABLE %s.%s;' % (self.options['athena_database'], self.options['athena_table']))
        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot make partition')

        stime = datetime.datetime.utcfromtimestamp(int(self.options['query_stime'] / 1000))
        etime = datetime.datetime.utcfromtimestamp(int(self.options['query_etime'] / 1000))

        q = ''
        q += " tid = '%s'" % self.options['query_tid']
        q += ' AND year * 10000 + month * 100 + day >= %s' % stime.strftime('%Y%m%d')
        q += ' AND year * 10000 + month * 100 + day <= %s' % etime.strftime('%Y%m%d')
        q += " AND datetime >= timestamp '%s'" % (stime.strftime('%Y-%m-%d %H:%M:%S'))
        q += " AND datetime <= timestamp '%s'" % (etime.strftime('%Y-%m-%d %H:%M:%S'))

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
            if url and url not in urls:
                urls.append(url)

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
datet, url, COUNT(y) as s_count, SUM(CAST(y as decimal)) as sum_scroll_y, MAX(CAST(y as decimal)) as max_scroll_y
FROM 
(
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
MAX(JSON_EXTRACT_SCALAR(qs, '$.o_e_y')) as y,
JSON_EXTRACT_SCALAR(qs, '$.cid') as uid
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'scroll_%' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'),  JSON_EXTRACT_SCALAR(qs, '$.cid')
) tmp 
GROUP BY datet, url  
),

event as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
COUNT(datetime) as event_count
FROM {0}.{1}
WHERE {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl')
),

widget_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
COUNT(datetime) as w_click_count
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_widget_%' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl')
),

trivial_click as (
SELECT 
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
COUNT(datetime) as t_click_count
FROM {0}.{1}
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'click_trivial_%' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl')
)

SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datetime,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
COUNT(qs) as count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.o_psid')) as session_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as user_count,
scroll.s_count,
scroll.sum_scroll_y,
scroll.max_scroll_y,
event.event_count,
widget_click.w_click_count,
trivial_click.t_click_count,
COUNT(JSON_EXTRACT_SCALAR(qs, '$.plt')) as plt_count,
SUM(CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal)) as sum_plt,
MAX(CAST(JSON_EXTRACT_SCALAR(qs, '$.plt') as decimal)) as max_plt
FROM 
{0}.{1}
LEFT OUTER JOIN 
scroll ON (scroll.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND scroll.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
event ON (event.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND event.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
widget_click ON (widget_click.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND widget_click.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
LEFT OUTER JOIN 
trivial_click ON (trivial_click.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND trivial_click.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview' AND {2}
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), s_count, sum_scroll_y, max_scroll_y, event_count, w_click_count, t_click_count
ORDER BY count DESC
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql2)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        target = self.s3.Object(self.options['target_bucket'], self.options['target_name'])
        target_raw = self.s3.Object(self.options['target_bucket'], self.options['target_name_raw'])

        table_result = []
        for index, row in pd_data.iterrows():
            url = self._normalizeUrl(row['url'])
            rj = json.loads(row.to_json())
            r = [d for d in table_result if d['url'] == url and d['datetime'] == rj['datetime']]
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
                t_result['avg_plt'] = t_result['avg_plt'] / t_result['plt_count']
            else:
                t_result['svg_plt'] = None

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
    parser.add_argument('-d', '--database', dest='athena_database', required=True, help='athena database')
    parser.add_argument('-p', '--table', dest='athena_table', required=True, help='athena table')
    parser.add_argument('--result-bucket', dest='athena_result_bucket', required=True, help='athena result bucket')
    parser.add_argument('--result-prefix', dest='athena_result_prefix', help='athena result object prefix', default='')
    parser.add_argument('-t', '--target-bucket', dest='target_bucket', required=True, help='target bucket')
    parser.add_argument('-n', '--target-prefix', dest='target_prefix', required=True, help='target key prefix')
    parser.add_argument('-r', '--target-prefix-raw', dest='target_prefix_raw', required=True, help='target key prefix')
    parser.add_argument('--target-suffix', dest='target_suffix', required=False, help='target key suffix')
    parser.add_argument('--query-tid', dest='query_tid', required=True, help='tid (Container Name)')
    parser.add_argument('--query-stime', dest='query_stime', type=int, required=True,
                        help='Query start time (msec unix time)')
    parser.add_argument('--query-etime', dest='query_etime', type=int, required=True,
                        help='Query end time (msec unix time)')

    args = vars(parser.parse_args())

    target_name = time.strftime("%Y%m%d%H%M%S") + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_stime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_etime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    if args['target_suffix']:
        target_name += args['target_suffix'] + '_'
    target_name += str(uuid.uuid4())

    args['target_name'] = args['target_prefix'] + target_name + '.json'
    args['target_name_raw'] = args['target_prefix_raw'] + target_name + '.json'

    retriever = DataRetriever(**args)
    retriever.execute()


if __name__ == '__main__':
    main()
