from retriever_base import RetrieverBase
from datetime import datetime, timedelta
import json
import os
import re
import pandas as pd

class GoalDataRetriever(RetrieverBase):
    def __init__(self, **kwargs):
        super(GoalDataRetriever, self).__init__(**kwargs)
        self.today = datetime.today()
        self.yesterday = self.today - timedelta(days=1)

    def execute(self):
        goal_obj = self.s3.Object(self.options['stat_bucket'],
                                  self.options['stat_prefix'] + self.options['goal_object'])
        goal_data = json.loads(goal_obj.get()['Body'].read())
        for g in goal_data:
            self.execute_result_yesterday(g)

    def execute_full_result(self, g):
        # TODO: implement it
        False

    def execute_result_yesterday(self, g):
        q = ''
        q += "tid = '{0}'".format(g['container'])
        q += ' AND year = {0}'.format(self.yesterday.strftime('%Y'))
        q += ' AND month = {0}'.format(self.yesterday.strftime('%-m'))
        q += ' AND day = {0}'.format(self.yesterday.strftime('%-d'))

        # support eq mode only
        q += " AND JSON_EXTRACT_SCALAR(qs, '$.o_s') = '{0}'".format(re.sub(r'\'', '\'\'', g['target']))

        if g['path']:
            # support eq mode only
            q += " AND regexp_like(JSON_EXTRACT_SCALAR(qs, '$.dl'), '^http?://[^/]+{0}$')".format(re.sub(r'\'', '\'\'', g['path']))

        sql = """SELECT 
COUNT(qs) as e_count,
COUNT(DISTINCT JSON_EXTRACT_SCALAR(qs, '$.cid')) as u_count
FROM {0}.{1}
WHERE {2}
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result = self._execute_athena_query(sql)
        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            print(json.dumps({'message': 'error', 'result': result}))
            return False

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        e_count = pd_data.iloc[0]['e_count']
        u_count = pd_data.iloc[0]['u_count']
        r_data = {'date': self.yesterday.strftime('%Y-%m-%d'), 'e_count': e_count, 'u_count': u_count}
        print(r_data)

def main():
    retriever = GoalDataRetriever(
        stat_bucket=os.environ.get('OTM_STATS_BUCKET'),
        stat_prefix=os.environ.get('OTM_STATS_PREFIX'),
        goal_object='goals.json',
        athena_result_bucket=os.environ.get('STATS_ATHENA_RESULT_BUCKET'),
        athena_result_prefix=os.environ.get('STATS_ATHENA_RESULT_PREFIX') or '',
        athena_database=os.environ.get('STATS_ATHENA_DATABASE'),
        athena_table=os.environ.get('STATS_ATHENA_TABLE')
    )
    retriever.execute()


if __name__ == '__main__':
    main()
