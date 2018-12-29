from google.cloud import bigquery
from google.oauth2 import service_account
import time
import boto3
import argparse
import json
import uuid
import datetime


class DataRetriever:
    def load_config_json(self, bucket_name, key):
        bucket = self.s3.Bucket(bucket_name)
        gcloud_key = bucket.Object(key)
        j = json.loads(gcloud_key.get()['Body'].read().decode('utf-8'))
        return service_account.Credentials.from_service_account_info(j)

    def __init__(self, **kwargs):
        self.options = kwargs
        self.s3 = boto3.resource('s3')

    def execute(self):
        credential = self.load_config_json(self.options['config_bucket'], self.options['gcloud_key'])
        client = bigquery.Client(project=credential.project_id, credentials=credential)

        q = ''
        q += 'JSON_EXTRACT_SCALAR(qs_json, "$.tid") = "%s"' % self.options['query_tid']
        q += ' AND datetime >= MSEC_TO_TIMESTAMP(%s)' % self.options['query_stime']
        q += ' AND datetime < MSEC_TO_TIMESTAMP(%s)' % self.options['query_etime']

        sql = """SELECT 
JSON_EXTRACT_SCALAR(qs_json, "$.dl") AS url,
JSON_EXTRACT_SCALAR(qs_json, "$.o_pl") AS p_url,
JSON_EXTRACT_SCALAR(qs_json, "$.dt") AS title,
JSON_EXTRACT_SCALAR(qs_json, "$.o_s") AS state,
JSON_EXTRACT_SCALAR(qs_json, "$.o_ps") AS p_state,
JSON_EXTRACT_SCALAR(qs_json, "$.el") AS label,
JSON_EXTRACT_SCALAR(qs_json, "$.o_xpath") AS xpath,
JSON_EXTRACT_SCALAR(qs_json, "$.o_a_id") AS a_id,
JSON_EXTRACT_SCALAR(qs_json, "$.o_a_class") AS class,
COUNT(qs_json) AS c
FROM TABLE_DATE_RANGE([%s.%s_], TIMESTAMP('%s'), TIMESTAMP('%s'))
WHERE %s
GROUP BY url, p_url, title, state, p_state, label, xpath, a_id, class
""" % (self.options['bq_dataset'],
       self.options['bq_table_prefix'],
       datetime.datetime.fromtimestamp(int((self.options['query_stime'] - 3600000) / 1000)).strftime('%Y-%m-%d'),
       datetime.datetime.fromtimestamp(int(self.options['query_etime'] / 1000)).strftime('%Y-%m-%d'), q)
        print('Execute query')
        print(sql)
        # TODO: change to Standard SQL
        config = bigquery.QueryJobConfig()
        config.use_legacy_sql = True
        query_job = client.query(sql, job_config=config)
        print(str(query_job.job_id))
        result = []
        for row in query_job:
            result.append({'url': row['url'], 'p_url': row['p_url'], 'title': row['title'], 'state': row['state'], 'p_state': row['p_state'],
                           'label': row['label'], 'xpath': row['xpath'], 'a_id': row['a_id'], 'class': row['class'],
                           'count': row['c']})

        s3 = boto3.resource('s3')
        target = s3.Object(self.options['target_bucket'], self.options['target_name'])
        print('s3://' + self.options['target_bucket'] + '/' + self.options['target_name'])
        print(result)
        target.put(Body=json.dumps({
            'meta': {
                'stime': self.options['query_stime'],
                'etime': self.options['query_etime'],
                'tid': self.options['query_tid']
            },
            'result': result
        }, ensure_ascii=False), ContentType='application/json; charset=utf-8')


def main():
    parser = argparse.ArgumentParser(description='Make stats from BigQuery')
    parser.add_argument('-c', '--config-bucket', dest='config_bucket', required=True, help='config bucket name')
    parser.add_argument('-k', '--gcloud-key-name', dest='gcloud_key', required=True, help='gcloud key place')
    parser.add_argument('-d', '--dataset', dest='bq_dataset', required=True, help='bq dataset')
    parser.add_argument('-p', '--table-prefix', dest='bq_table_prefix', required=True, help='bq table prefix')
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
    target_name += datetime.datetime.fromtimestamp(int(args['query_stime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    target_name += datetime.datetime.fromtimestamp(int(args['query_etime'] / 1000)).strftime('%Y%m%d%H%M%S') + '_'
    if args['target_suffix']:
        target_name += args['target_suffix'] + '_'
    target_name += str(uuid.uuid4()) + '.json'

    args['target_name'] = target_name

    retriever = DataRetriever(**args)
    retriever.execute()


if __name__ == '__main__':
    main()
