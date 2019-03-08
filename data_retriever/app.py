from retrying import retry
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

    def execute(self):
        result = self._execute_athena_query(
            'MSCK REPAIR TABLE %s.%s;' % (self.options['athena_database'], self.options['athena_table']))
        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot make partition')

        stime = datetime.datetime.utcfromtimestamp(int(self.options['query_stime'] / 1000))
        etime = datetime.datetime.utcfromtimestamp(int(self.options['query_etime'] / 1000))

        q = ''
        q += " tid = '%s'" % self.options['query_tid']
        q += ' AND year >= %s AND year <= %s' % (stime.strftime('%Y'), etime.strftime('%Y'))
        q += ' AND month >= %s AND month <= %s' % (stime.strftime('%-m'), etime.strftime('%-m'))
        q += ' AND day >= %s AND day <= %s' % (stime.strftime('%-d'), etime.strftime('%-d'))
        q += " AND datetime >= timestamp '%s'" % (stime.strftime('%Y-%m-%d %H:%M:%S'))
        q += " AND datetime <= timestamp '%s'" % (etime.strftime('%Y-%m-%d %H:%M:%S'))

        sql = """SELECT * , COUNT(*) as count
FROM 
(SELECT 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS url,
JSON_EXTRACT_SCALAR(qs, '$.o_pl') AS p_url,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS title,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.o_ps') AS p_state,
JSON_EXTRACT_SCALAR(qs, '$.el') AS label,
JSON_EXTRACT_SCALAR(qs, '$.o_xpath') AS xpath,
JSON_EXTRACT_SCALAR(qs, '$.o_a_id') AS a_id,
JSON_EXTRACT_SCALAR(qs, '$.o_a_class') AS class
FROM %s.%s
WHERE %s
) tmp
GROUP BY url, p_url, title, state, p_state, label, xpath, a_id, class 
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
SELECT
JSON_EXTRACT_SCALAR(qs, '$.dl') as url,
JSON_EXTRACT_SCALAR(qs, '$.o_s') as state, 
COUNT(qs) as count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.o_psid')) as session_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as user_count
FROM %s.%s
WHERE %s
GROUP BY JSON_EXTRACT_SCALAR(qs, '$.dl'), JSON_EXTRACT_SCALAR(qs, '$.o_s')
ORDER BY count DESC
""" % (self.options['athena_database'], self.options['athena_table'], q)

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
            'table': table_result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')

def main():
    parser = argparse.ArgumentParser(description='Make stats from BigQuery')
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
