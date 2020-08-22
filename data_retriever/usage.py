from retriever_base import RetrieverBase
import boto3
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from decimal import Decimal


class UsageRetriever(RetrieverBase):
    def __init__(self, **kwargs):
        super(UsageRetriever, self).__init__(**kwargs)
        if self.options['date']:
            self.today = datetime.strptime(self.options['date'], '%Y-%m-%d')
        else:
            self.today = datetime.today()
        self.lastmonth = self.today - relativedelta(months=1)

    def execute(self):
        self.make_partition()

        q = 'year = %s' % self.lastmonth.year
        q += ' AND month = %s' % self.lastmonth.month

        sql = """SELECT
type, org, tid, SUM(size) as size
FROM {0}.{1}
WHERE {2}
GROUP BY type, org, tid
""".format(self.options['athena_database'], self.options['athena_table'], q)

        result_athena = self._execute_athena_query(sql)
        if result_athena['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot execute query')

        result = {}

        result_data = self.s3.Bucket(self.options['athena_result_bucket']).Object(
            '%s%s.csv' % (
                self.options['athena_result_prefix'], result_athena['QueryExecution']['QueryExecutionId'])).get()
        pd_data = pd.read_csv(result_data['Body'], encoding='utf-8')
        for index, row in pd_data.iterrows():
            org = row['org']
            if org not in result:
                result[org] = {'athena_scan_size': Decimal(0), 'collect_size': Decimal(0), 'details': []}
            tid = None
            if not pd.isna(row['tid']):
                tid = row['tid']
            record = {'type': row['type'], 'tid': tid, 'size': Decimal(row['size'])}
            if row['type'] == 'athena_scan':
                result[org]['athena_scan_size'] += row['size']
            if row['type'] == 'collect':
                result[org]['collect_size'] += row['size']
            result[org]['details'].append(record)

        dynamodb = boto3.resource('dynamodb')
        dynamodb_table = dynamodb.Table(self.options['usage_table'])
        for org in result:
            dynamodb_table.put_item(Item=dict(
                result[org],
                **{'organization': org, 'month': Decimal(self.lastmonth.year * 1000 + self.lastmonth.month)}
            ))


def main():
    args = {}
    args['date'] = os.environ.get('DATE')
    args['athena_result_bucket'] = os.environ.get('STATS_ATHENA_RESULT_BUCKET')
    args['athena_result_prefix'] = os.environ.get('STATS_ATHENA_RESULT_PREFIX') or ''
    args['athena_database'] = os.environ.get('STATS_ATHENA_DATABASE')
    args['athena_table'] = os.environ.get('USAGE_ATHENA_TABLE')
    args['usage_table'] = os.environ.get('OTM_USAGE_DYNAMODB_TABLE')

    retriever = UsageRetriever(**args)
    retriever.execute()


if __name__ == '__main__':
    main()
