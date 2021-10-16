from retrying import retry
import boto3
import json
import datetime


class RetrieverBase:
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

    def _save_usage_report(self, bucket, org, tid, result_athena):
        print(json.dumps({'message': 'save usage report'}))
        scanned = result_athena['QueryExecution']['Statistics']['DataScannedInBytes']
        usage_key = 'org={0}/tid={1}/{2}/{3}.json'.format(org, tid,
                                                          datetime.datetime.now().strftime('year=%Y/month=%-m/day=%-d'),
                                                          result_athena['QueryExecution']['QueryExecutionId'])
        usage_key = '{0}{1}'.format(self.options['usage_prefix'], usage_key)
        self.s3.Object(bucket, usage_key).put(Body=json.dumps({'type': 'athena_scan', 'size': scanned}))

    def make_partition(self):
        result = self._execute_athena_query('MSCK REPAIR TABLE %s.%s;' % (self.options['athena_database'], self.options['athena_table']))

        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot make partition')
