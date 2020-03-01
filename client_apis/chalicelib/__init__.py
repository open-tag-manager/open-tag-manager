from chalice import CognitoUserPoolAuthorizer
import os
from boto3.dynamodb.conditions import Key
from botocore.errorfactory import ClientError
import boto3
import json
import copy

from .script_generator import ScriptGenerator
from .upload import S3Uploader

authorizer = CognitoUserPoolAuthorizer('UserPool', provider_arns=[str(os.environ.get('OTM_COGNITO_USER_POOL_ARN'))])
dynamodb = boto3.resource('dynamodb')
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
batch_client = boto3.client('batch')


def get_role_table():
    return dynamodb.Table(str(os.environ.get('OTM_ROLE_DYNAMODB_TABLE')))


def get_roles(app):
    if 'authorizer' in app.current_request.context:
        username = app.current_request.context['authorizer']['claims']['cognito:username']

        item = get_role_table().query(
            KeyConditionExpression=Key('username').eq(username)
        )
        if not 'Items' in item:
            return []

        result = []
        for role in item['Items']:
            result.append({'org': role['organization'], 'roles': role['roles']})
    else:
        # for local test environment
        result = [{'org': 'root', 'roles': ['write', 'read']}, {'org': 'sample', 'roles': ['write', 'read']}]

    freezed_orgs = []
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').get()
        freezed_orgs = json.loads(response['Body'].read())
    except ClientError:
        pass

    for item in result:
        item['freezed'] = item['org'] in freezed_orgs

    return result


def has_role(app, org, role_name):
    for role in get_roles(app):
        if (role['org'] == org or role['org'] == 'root') and role_name in role['roles']:
            if org == 'root':
                return True

            if role_name == 'write':
                return not role['freezed']
            else:
                return True

    return False


def get_config_data(org):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), prefix + 'config.json').get()
        return json.loads(response['Body'].read())
    except ClientError:
        return {}


def put_config_data(org, config):
    prefix = ''
    if org != 'root':
        prefix = org + '/'
    s3.Object(os.environ.get('OTM_BUCKET'), prefix + 'config.json').put(Body=json.dumps(config),
                                                                        ContentType='application/json')


def get_container_data(org, name, config):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    containers = config['containers']
    c = list(filter(lambda x: x['name'] == name, containers))
    if len(c) <= 0:
        return (None, None)

    container = c[0]
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + prefix + name + '.json').get()
        return (json.loads(response['Body'].read()), container)
    except ClientError:
        return (copy.copy(container), container)
