from chalice import CognitoUserPoolAuthorizer, Chalice
import os
import boto3
import re

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
