from chalice import CognitoUserPoolAuthorizer, Chalice, Response
from cerberus import Validator
import os
from boto3.dynamodb.conditions import Key
import boto3
import re

from .script_generator import ScriptGenerator
from .upload import S3Uploader

app = Chalice(app_name="open_tag_manager")
app.debug = bool(os.environ.get('DEBUG'))
app.experimental_feature_flags.update(['BLUEPRINTS'])

authorizer = CognitoUserPoolAuthorizer('UserPool', provider_arns=[str(os.environ.get('OTM_COGNITO_USER_POOL_ARN'))])
dynamodb = boto3.resource('dynamodb')
cognito_idp_client = boto3.client('cognito-idp')
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
batch_client = boto3.client('batch')


def get_cognito_user_pool_id():
    return re.search(r"/(.+)$", os.environ.get('OTM_COGNITO_USER_POOL_ARN'))[1]


def get_role_table():
    return dynamodb.Table(str(os.environ.get('OTM_ROLE_DYNAMODB_TABLE')))


def get_user_table():
    return dynamodb.Table(str(os.environ.get('OTM_USER_DYNAMODB_TABLE')))


def get_org_table():
    return dynamodb.Table(str(os.environ.get('OTM_ORG_DYNAMODB_TABLE')))


def get_stat_table():
    return dynamodb.Table(str(os.environ.get('OTM_STAT_DYNAMODB_TABLE')))


def get_container_table():
    return dynamodb.Table(str(os.environ.get('OTM_CONTAINER_DYNAMODB_TABLE')))


def get_current_user_name():
    if 'authorizer' in app.current_request.context:
        return app.current_request.context['authorizer']['claims']['cognito:username']

    # local environment
    return os.environ.get('TEST_USER') or 'root'


def has_permission(org, role):
    item = get_role_table().query(
        KeyConditionExpression=Key('username').eq(get_current_user_name())
    )
    for r in item['Items']:
        if r['organization'] == 'root' and 'admin' in r['roles']:
            return True

        if r['organization'] == org and role in r['roles']:
            return True

    return False


def check_container_permission():
    def __decorator(func):
        def inner(*args, **kwargs):
            org = app.current_request.uri_params['org']
            name = app.current_request.uri_params['name']
            container_info = get_container_table().get_item(Key={'organization': org, 'tid': name})
            if not 'Item' in container_info:
                return Response(body={'error': 'not found'}, status_code=404)

            return func(*args, **kwargs)

        return inner

    return __decorator


def check_org_permission(role):
    def __decorator(func):
        def inner(*args, **kwargs):
            org = app.current_request.uri_params['org']
            if not has_permission(org, role):
                return Response(body={'error': 'permission error'}, status_code=401)
            return func(*args, **kwargs)

        return inner

    return __decorator


def check_root_admin():
    def __decorator(func):
        def inner(*args, **kwargs):
            if not has_permission('root', 'admin'):
                return Response(body={'error': 'permission error'}, status_code=401)
            return func(*args, **kwargs)

        return inner

    return __decorator


def check_json_body(schema):
    def __decorator(func):
        def inner(*args, **kwargs):
            request = app.current_request.json_body
            v = Validator(schema)
            if v.validate(request):
                return func(*args, **kwargs)
            else:
                return Response(body={'error': 'bad request', 'error_fields': v.errors}, status_code=400)

        return inner

    return __decorator
