from chalice import CognitoUserPoolAuthorizer, Chalice
import os
import boto3
import re
import uuid
import datetime
import json
import hashlib

from .script_generator import ScriptGenerator
from .upload import S3Uploader

app = Chalice(app_name="open_tag_manager")
app.debug = bool(os.environ.get('DEBUG'))
app.experimental_feature_flags.update(['BLUEPRINTS'])

authorizer = CognitoUserPoolAuthorizer('UserPool', provider_arns=[str(os.environ.get('OTM_COGNITO_USER_POOL_ARN'))])
cognito_idp_client = boto3.client('cognito-idp')

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

batch_client = boto3.client('batch')

athena_client = boto3.client('athena')


def get_cognito_user_pool_id():
    return re.search(r"/(.+)$", os.environ.get('OTM_COGNITO_USER_POOL_ARN'))[1]


def get_current_user_name():
    if 'authorizer' in app.current_request.context:
        return app.current_request.context['authorizer']['claims']['cognito:username']

    # local environment
    return os.environ.get('TEST_USER') or 'root'


def execute_athena_query(query, token=None):
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': os.environ.get('STATS_ATHENA_DATABASE')
        },
        ResultConfiguration={
            'OutputLocation': 's3://%s/' % (os.environ.get('STATS_ATHENA_RESULT_BUCKET')),
            'EncryptionConfiguration': {
                'EncryptionOption': 'SSE_S3'
            }
        },
        ClientRequestToken='%s_%s' % (token, hashlib.sha1(query.encode('utf-8')).hexdigest()) or str(uuid.uuid4())
    )
    return response['QueryExecutionId']


def save_athena_usage_report(org, tid, result_athena):
    scanned = result_athena['QueryExecution']['Statistics']['DataScannedInBytes']
    usage_key = 'org={0}/tid={1}/{2}/{3}.json'.format(org, tid,
                                                      datetime.datetime.now().strftime('year=%Y/month=%-m/day=%-d'),
                                                      result_athena['QueryExecution']['QueryExecutionId'])
    usage_key = '{0}{1}'.format(os.environ.get('OTM_USAGE_PREFIX'), usage_key)
    s3.Object(os.environ.get('OTM_STATS_BUCKET'), usage_key).put(Body=json.dumps({'type': 'athena_scan', 'size': scanned}))
