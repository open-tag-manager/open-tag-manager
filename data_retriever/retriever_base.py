from retrying import retry
import boto3
import json


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

    def make_partition(self):
        result = self._execute_athena_query('MSCK REPAIR TABLE %s.%s;' % (self.options['athena_database'], self.options['athena_table']))

        if result['QueryExecution']['Status']['State'] != 'SUCCEEDED':
            raise Exception('Cannot make partition')
