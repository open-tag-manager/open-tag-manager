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

    def _get_swagger_helper(self, urls):
        tree = {
            'path': '',
            'exists': False,
            'children': []
        }

        def get_child_path(children, target_path):
            values = [child for child in children if child['path'] == target_path]
            return values[0] if values else None

        for url in urls:
            if not url:
                continue

            if url.lower() == 'undefined':
                continue

            paths = urlparse(url).path.split('/')

            if len(paths) == 1 or len(paths) == 2 and paths[1] == '':
                tree['exists'] = True
                continue

            current = tree
            for i in range(1, len(paths)):
                c = get_child_path(current['children'], paths[i])
                if c is None:
                    new_child = {
                        'path': paths[i],
                        'exists': False,
                        'children': []
                    }
                    current['children'].append(new_child)
                    c = new_child

                current = c

                if len(paths) - 1 == i:
                    c['exists'] = True

        result = []
        def check_child(path, children):
            for child in children:
                if child['exists']:
                    result.append(path + child['path'])
                check_child(path + child['path'] + '/', child['children'])

        if tree['exists']:
            result.append('/')

        check_child('/', tree['children'])
        result.reverse()

        swagger = {'paths': {}}
        for path in result:
            swagger['paths'][path] = {}

        return swagger

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

        sql = """
SELECT 
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
FROM %s.%s
WHERE %s
GROUP BY 
JSON_EXTRACT_SCALAR(qs, '$.dl'), 
JSON_EXTRACT_SCALAR(qs, '$.o_pl'),
JSON_EXTRACT_SCALAR(qs, '$.dt'),
JSON_EXTRACT_SCALAR(qs, '$.o_s'),
JSON_EXTRACT_SCALAR(qs, '$.o_ps'),
JSON_EXTRACT_SCALAR(qs, '$.el'),
JSON_EXTRACT_SCALAR(qs, '$.o_a_id')
""" % (self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        result = []
        for index, row in pd_data.iterrows():
            result.append(json.loads(row.to_json()))

        sql2 = """
WITH scroll  as (
SELECT 
datet, url, COUNT(y) as s_count, AVG(CAST(y as decimal)) as avg_scroll_y, MAX(CAST(y as decimal)) as max_scroll_y
FROM 
(
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datet,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
MAX(JSON_EXTRACT_SCALAR(qs, '$.o_e_y')) as y,
JSON_EXTRACT_SCALAR(qs, '$.cid') as uid
FROM %s.%s
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') LIKE 'scroll_%%'
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'),  JSON_EXTRACT_SCALAR(qs, '$.cid')
) tmp 
GROUP BY datet, url  
)
SELECT
format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ') as datetime,
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
COUNT(qs) as count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.o_psid')) as session_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as user_count,
scroll.s_count,
scroll.avg_scroll_y,
scroll.max_scroll_y
FROM 
%s.%s LEFT OUTER JOIN 
scroll ON (scroll.url = JSON_EXTRACT_SCALAR(qs, '$.dl') AND scroll.datet = format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'))
WHERE JSON_EXTRACT_SCALAR(qs, '$.o_s') = 'pageview' AND %s
GROUP BY format_datetime(datetime, 'yyyy-MM-dd HH:00:00ZZ'), JSON_EXTRACT_SCALAR(qs, '$.dl'), s_count, avg_scroll_y, max_scroll_y
ORDER BY count DESC
""" % (self.options['athena_database'], self.options['athena_table'], self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql2)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')

        target = self.s3.Object(self.options['target_bucket'], self.options['target_name'])

        table_result = []
        for index, row in pd_data.iterrows():
            table_result.append(json.loads(row.to_json()))

        urls = []
        for index, row in pd_data['url'].iteritems():
            urls.append(row)

        swagger = self._get_swagger_helper(urls)

        print(json.dumps({'message': 'dump data', 'bucket': 's3://' + self.options['target_bucket'] + '/' + self.options['target_name']}))
        print(json.dumps(result))
        print(json.dumps(table_result))

        target.put(Body=json.dumps({
            'meta': {
                'stime': self.options['query_stime'],
                'etime': self.options['query_etime'],
                'tid': self.options['query_tid'],
                'version': 2
            },
            'result': result,
            'table': table_result,
            'swagger_sample': swagger
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')

def main():
    parser = argparse.ArgumentParser(description='Make stats from Athena')
    parser.add_argument('-d', '--database', dest='athena_database', required=True, help='athena database')
    parser.add_argument('-p', '--table', dest='athena_table', required=True, help='athena table')
    parser.add_argument('--result-bucket', dest='athena_result_bucket', required=True, help='athena result bucket')
    parser.add_argument('--result-prefix', dest='athena_result_prefix', help='athena result object prefix', default='')
    parser.add_argument('-t', '--target-bucket', dest='target_bucket', required=True, help='target bucket')
    parser.add_argument('-n', '--target-prefix', dest='target_prefix', required=True, help='target key prefix')
    parser.add_argument('--target-suffix', dest='target_suffix', required=False, help='target key suffix')
    parser.add_argument('--query-tid', dest='query_tid', required=True, help='tid (Container Name)')
    parser.add_argument('--query-stime', dest='query_stime', type=int, required=True,
                        help='Query start time (msec unix time)')
    parser.add_argument('--query-etime', dest='query_etime', type=int, required=True,
                        help='Query end time (msec unix time)')

    args = vars(parser.parse_args())

    target_name = args['target_prefix'] + time.strftime("%Y%m%d%H%M%S") + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_stime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    target_name += datetime.datetime.utcfromtimestamp(int(args['query_etime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    if args['target_suffix']:
        target_name += args['target_suffix'] + '_'
    target_name += str(uuid.uuid4()) + '.json'

    args['target_name'] = target_name

    retriever = DataRetriever(**args)
    retriever.execute()


if __name__ == '__main__':
    main()
