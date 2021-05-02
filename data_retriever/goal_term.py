from retriever_base import RetrieverBase
from botocore.errorfactory import ClientError
import json
import os
import re
import boto3
import pandas as pd
import datetime


class GoalTermDataRetriever(RetrieverBase):
    def __init__(self, **kwargs):
        super(GoalTermDataRetriever, self).__init__(**kwargs)

    def execute(self):
        self.make_partition()

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(str(self.options['container_table']))
        container_info = table.get_item(Key={'tid': self.options['tid']})
        if 'Item' not in container_info:
            print(json.dumps({'message': 'container data is not found'}))
            return

        for goal in container_info['Item']['goals']:
            if goal['id'] == self.options['goal_id']:
                self.execute_query(container_info['Item']['organization'], self.options['tid'], goal)
                return

        print(json.dumps({'message': 'goal data is not found'}))
        return

    def execute_query(self, org, tid, g):
        q = ''
        q += "org = '{0}'".format(org)
        q += " AND tid = '{0}'".format(tid)
        q += ' AND  year * 10000 + month * 100 + day >= {0}'.format(self.options['startdate'])
        q += ' AND  year * 10000 + month * 100 + day <= {0}'.format(self.options['enddate'])

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
year * 10000 + month * 100 + day as date,
COUNT(qs) as e_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as u_count
FROM {0}.{1}
WHERE {2}
GROUP BY year * 10000 + month * 100 + day 
""".format(self.options['athena_database'], self.options['athena_table'], q)

        athena_result = self._execute_athena_query(sql)
        if athena_result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            print(athena_result)
            return False

        self._save_usage_report(self.options['stat_bucket'], org, tid, athena_result)

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

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object('%s%s.csv' % (
        self.options['athena_result_prefix'], athena_result['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        for index, row in pd_data.iterrows():
            e_count = int(row['e_count'])
            u_count = int(row['u_count'])
            r_data = {
                'date': datetime.datetime.strptime(str(row['date']), '%Y%m%d').strftime('%Y-%m-%d'),
                'e_count': e_count,
                'u_count': u_count
            }
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
    retriever = GoalTermDataRetriever(
        stat_bucket=os.environ.get('OTM_STATS_BUCKET'),
        stat_prefix=os.environ.get('OTM_STATS_PREFIX'),
        usage_prefix=os.environ.get('OTM_USAGE_PREFIX'),
        athena_result_bucket=os.environ.get('STATS_ATHENA_RESULT_BUCKET'),
        athena_result_prefix=os.environ.get('STATS_ATHENA_RESULT_PREFIX') or '',
        athena_database=os.environ.get('STATS_ATHENA_DATABASE'),
        athena_table=os.environ.get('STATS_ATHENA_TABLE'),
        container_table=os.environ.get('OTM_CONTAINER_DYNAMODB_TABLE'),
        tid=os.environ.get('TID'),
        goal_id=os.environ.get('GOAL_ID'),
        startdate=os.environ.get('STARTDATE'),
        enddate=os.environ.get('ENDDATE')
    )
    retriever.execute()


if __name__ == '__main__':
    main()
