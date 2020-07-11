from chalice import Response
from chalicelib import app, authorizer, get_current_user_name, check_root_admin, check_org_permission, \
    get_role_table, get_org_table, check_json_body, get_user_table, cognito_idp_client, get_cognito_user_pool_id
from chalicelib.container_routes import container_routes
from chalicelib.stats_routes import stats_routes
import importlib
import json
import os
import time
from decimal import Decimal

from boto3.dynamodb.conditions import Key


@app.route('/', cors=True, authorizer=authorizer)
def index():
    return {'success': True}


def get_user_response(username):
    user_info = get_user_table().get_item(Key={'username': username})
    item = get_role_table().query(
        KeyConditionExpression=Key('username').eq(username)
    )
    if not 'Item' in user_info:
        return Response(body={'error': 'not found'}, status_code=404)

    result = user_info['Item']
    result['orgs'] = []
    if 'Items' in item:
        for role in item['Items']:
            result['orgs'].append({'org': role['organization'], 'roles': role['roles']})
    return result


@app.route('/user', cors=True, authorizer=authorizer, methods=['GET'])
def get_current_user():
    username = get_current_user_name()
    return get_user_response(username)


@app.route('/users/{username}', cors=True, authorizer=authorizer, methods=['GET'])
@check_root_admin()
def get_user(username):
    return get_user_response(username)


@app.route('/users', cors=True, authorizer=authorizer, methods=['GET'])
@check_root_admin()
def get_all_users():
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'Limit': 100
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = get_user_table().scan(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            result = {
                'username': item['username'],
                'created_at': item['created_at'] if 'created_at' in item else None,
                'updated_at': item['updated_at'] if 'updated_at' in item else None,
                'email': item['email'] if 'email' in item else None
            }
            results.append(result)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response(results, headers=headers)


@app.route('/users', cors=True, authorizer=authorizer, methods=['POST'])
@check_json_body({
    'username': {'type': 'string', 'required': True},
    'email': {'type': 'string', 'required': True, 'empty': False}
})
@check_root_admin()
def create_new_user():
    # register to Cognito
    r = app.current_request.json_body
    user_info = get_user_table().get_item(Key={'username': r['username']})
    if not 'Item' in user_info:
        cognito_idp_client.admin_create_user(
            UserPoolId=get_cognito_user_pool_id(), Username=r['username'],
            UserAttributes=[
                {'Name': 'email', 'Value': r['email']},
                {'Name': 'email_verified', 'Value': 'true'}
            ])
        # register to dynamoDB
        ts = Decimal(time.time())
        data = {'username': r['username'], 'email': r['email'], 'created_at': ts, 'updated_at': ts}
        get_user_table().put_item(Item=data)
    else:
        return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs', cors=True, authorizer=authorizer, methods=['GET'])
@check_root_admin()
def organizations():
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'Limit': 100
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = get_org_table().scan(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            result = {
                'name': item['name'],
                'created_at': item['created_at'] if 'created_at' in item else None,
                'updated_at': item['updated_at'] if 'updated_at' in item else None
            }
            results.append(result)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response(results, headers=headers)


@app.route('/orgs', cors=True, authorizer=authorizer, methods=['POST'])
@check_root_admin()
@check_json_body({'name': {'type': 'string', 'required': True, 'empty': False}})
def create_organization():
    r = app.current_request.json_body
    org_info = get_org_table().get_item(Key={'name': r['name']})
    if not 'Item' in org_info:
        ts = Decimal(time.time())
        data = {'name': r['name'], 'created_at': ts, 'updated_at': ts}
        get_org_table().put_item(Item=data)
        return Response(body=data, status_code=201)
    else:
        return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs/{org}', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def organization_info(org):
    org_info = get_org_table().get_item(Key={'name': org})
    if 'Item' in org_info:
        return org_info['Item']
    else:
        return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/users', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('admin')
@check_json_body({'username': {'type': 'string', 'required': True},
                  'roles': {'type': 'list', 'allowed': ['admin', 'read', 'write']}})
def invite_org_user(org):
    r = app.current_request.json_body
    response = get_role_table().get_item(Key={'organization': org, 'username': r['username']})
    if not 'Item' in response:
        get_role_table().put_item(Item={'organization': org, 'username': r['username'], 'roles': r['roles']})
        return Response({'username': r['username'], 'organization': org, 'roles': r['roles']}, status_code=201)

    return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs/{org}/users/{username}', methods=['DELETE'], cors=True, authorizer=authorizer)
@check_org_permission('admin')
def remove_org_user(org, username):
    response = get_role_table().get_item(Key={'organization': org, 'username': username})
    if 'Item' in response:
        get_role_table().delete_item(Key={'organization': org, 'username': username})
        return Response(body=None, status_code=204)

    return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/users', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def org_users(org):
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'KeyConditionExpression': Key('organization').eq(org),
        'IndexName': 'organization_index',
        'Limit': 100,
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = get_role_table().query(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            result = {'username': item['username'], 'roles': item['roles']}
            results.append(result)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response(results, headers=headers)


app.register_blueprint(container_routes, url_prefix='/orgs/{org}/containers')
app.register_blueprint(stats_routes, url_prefix='/orgs/{org}/containers/{name}/stats')

plugins = json.loads(os.environ.get('OTM_PLUGINS'), encoding='utf-8')
for plugin in plugins:
    module = importlib.import_module('chalicelib.otmplugins.' + plugin['package'] + '.' + plugin['module'])
    app.register_blueprint(module.plugin_app, url_prefix=plugin['urlPrefix'])
