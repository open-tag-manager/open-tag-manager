from retriever_base import RetrieverBase
from datetime import datetime, timedelta
from botocore.errorfactory import ClientError
import json
import os
import re
import boto3
import pandas as pd


class GoalDataRetriever(RetrieverBase):
    def __init__(self, **kwargs):
        super(GoalDataRetriever, self).__init__(**kwargs)
        print(self.options)
        if self.options['date']:
            self.today = datetime.strptime(self.options['date'], '%Y-%m-%d')
        else:
            self.today = datetime.today()
        self.yesterday = self.today - timedelta(days=1)

    def execute(self):
        self.make_partition()
        self.scan_table()

    def scan_table(self, last_evaluated_key=None):
        args = {
            'FilterExpression': 'attribute_exists(goals)'
        }
        if last_evaluated_key:
            args['ExclusiveStartKey'] = last_evaluated_key

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(str(self.options['container_table']))
        items = table.scan(**args)
        for item in items['Items']:
            for g in item['goals']:
                self.execute_result_yesterday(item['organization'], item['tid'], g)
        if 'LastEvaluatedKey' in items:
            self.scan_table(items['LastEvaluatedKey'])

    def execute_result_yesterday(self, org, tid, g):
        q = ''
        q += "org = '{0}'".format(org)
        q += " AND tid = '{0}'".format(tid)
        q += ' AND year = {0}'.format(self.yesterday.strftime('%Y'))
        q += ' AND month = {0}'.format(self.yesterday.month)
        q += ' AND day = {0}'.format(self.yesterday.day)

        if g['target_match'] == 'prefix':
            q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.o_s'), '^{0}')".format(
                re.sub(r'\'', '\'\'', re.escape(g['target'])))
        elif g['target_match'] == 'regex':
            q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.o_s'), '{0}')".format(re.sub(r'\'', '\'\'', g['target']))
        else:
            # eq
            q += " AND JSON_EXTRACT_SCALAR(qs, '$.o_s') = '{0}'".format(re.sub(r'\'', '\'\'', g['target']))

        if 'path' in g and g['path']:
            if g['path_match'] == 'prefix':
                q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.dl'), '^https?://[^/]+{0}')".format(
                    re.sub(r'\'', '\'\'', re.escape(g['path'])))
            elif g['target_match'] == 'regex':
                q += " AND regexp_like(regexp_replace(JSON_EXTRACT_SCALAR(qs, '$.dl'), '^https?://[^/]+', ''), '{0}')".format(
                    re.sub(r'\'', '\'\'', g['path']))
            else:
                # eq
                q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.dl'), '^https?://[^/]+{0}$')".format(
                    re.sub(r'\'', '\'\'', re.escape(g['path'])))

        if 'label' in g and g['label']:
            if g['label_match'] == 'prefix':
                q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.el'), '^{0}')".format(
                    re.sub(r'\'', '\'\'', re.escape(g['label'])))
            elif g['target_match'] == 'regex':
                q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.el'), '{0}')".format(
                    re.sub(r'\'', '\'\'', g['label']))
            else:
                # eq
                q += " AND JSON_EXTRACT_SCALAR(qs, '$.el') = '{0}'".format(re.sub(r'\'', '\'\'', g['label']))

        sql = """SELECT 
COUNT(qs) as e_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as u_count
FROM {0}.{1}
WHERE {2}
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result = self._execute_athena_query(sql)
        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            print(result)
            return False

        self._save_usage_report(self.options['stat_bucket'], org, tid, result)

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        e_count = int(pd_data.iloc[0]['e_count'])
        u_count = int(pd_data.iloc[0]['u_count'])
        r_data = {'date': self.yesterday.strftime('%Y-%m-%d'), 'e_count': e_count, 'u_count': u_count}

        grp_prefix = ''
        if not org == 'root':
            grp_prefix = org + '/'

        result_file = self.options['stat_prefix'] + grp_prefix + tid + '_' + g['id'] + '_goal_result.json'
        goal_result_obj = self.s3.Object(self.options['stat_bucket'], result_file)
        try:
            response = goal_result_obj.get()
            result = json.loads(response['Body'].read())
        except ClientError:
            result = []

        idx = [i for i, _ in enumerate(result) if _['date'] == r_data['date']]
        if len(idx) > 0:
            result[idx[0]] = r_data
        else:
            result.append(r_data)

        result.sort(key=lambda x: x['date'])
        print(json.dumps(
            {'message': 'save goal result data', 'bucket': self.options['stat_bucket'], 'file': result_file}))
        goal_result_obj.put(Body=json.dumps(result), ContentType='application/json')


def main():
    retriever = GoalDataRetriever(
        stat_bucket=os.environ.get('OTM_STATS_BUCKET'),
        stat_prefix=os.environ.get('OTM_STATS_PREFIX'),
        usage_prefix=os.environ.get('OTM_USAGE_PREFIX'),
        athena_result_bucket=os.environ.get('STATS_ATHENA_RESULT_BUCKET'),
        athena_result_prefix=os.environ.get('STATS_ATHENA_RESULT_PREFIX') or '',
        athena_database=os.environ.get('STATS_ATHENA_DATABASE'),
        athena_table=os.environ.get('STATS_ATHENA_TABLE'),
        container_table=os.environ.get('OTM_CONTAINER_DYNAMODB_TABLE'),
        date=os.environ.get('DATE')
    )
    retriever.execute()


if __name__ == '__main__':
    main()
