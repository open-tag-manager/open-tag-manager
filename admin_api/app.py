from chalice import Response
from chalicelib import app, authorizer, get_current_user_name, cognito_idp_client, get_cognito_user_pool_id, athena_client, execute_athena_query
import chalicelib.decorator as decorator
import chalicelib.dynamodb as dynamodb
from chalicelib.container_routes import container_routes
from chalicelib.stats_routes import stats_routes
from chalicelib.usage_routes import usage_routes
from chalicelib.goal_routes import goal_routes
from chalicelib.payment_routes import payment_routes
from chalicelib.container_users_routes import users_routes
import json
import os
import time
from decimal import Decimal

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeDeserializer

deser = TypeDeserializer()


@app.route('/', cors=True, authorizer=authorizer)
def index():
    return {'success': True}


def get_user_response(username):
    user_info = dynamodb.get_user_table().get_item(Key={'username': username})
    if 'Item' in user_info:
        result = user_info['Item']
    else:
        try:
            idp_user = cognito_idp_client.admin_get_user(UserPoolId=get_cognito_user_pool_id(), Username=username)
        except ClientError as error:
            if error.response['Error']['Code'] == 'UserNotFoundException':
                return Response(body={'error': 'not found'}, status_code=404)
            else:
                raise error

        email = [x for x in idp_user['UserAttributes'] if x['Name'] == 'email'][0]['Value']
        ts = Decimal(time.time())
        data = {'username': username, 'email': email, 'created_at': ts, 'updated_at': ts}
        dynamodb.get_user_table().put_item(Item=data)
        result = data

    item = dynamodb.get_role_table().query(
        KeyConditionExpression=Key('username').eq(username)
    )

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
@decorator.check_root_admin()
def get_user(username):
    return get_user_response(username)


@app.route('/users/{username}', cors=True, authorizer=authorizer, methods=['DELETE'])
@decorator.check_root_admin()
def delete_user(username):
    user_info = get_user_response(username)
    if not user_info:
        return Response(body={'error': 'not found'}, status_code=400)

    role_info = dynamodb.get_role_table().query(
        KeyConditionExpression=Key('username').eq(username)
    )

    for role in role_info['Items']:
        dynamodb.get_role_table().delete_item(Key={'username': username, 'organization': role['organization']})

    dynamodb.get_user_table().delete_item(Key={'username': username})
    cognito_idp_client.admin_delete_user(UserPoolId=get_cognito_user_pool_id(), Username=username)
    return Response(body=None, status_code=204)


@app.route('/users', cors=True, authorizer=authorizer, methods=['GET'])
@decorator.check_root_admin()
def get_all_users():
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'Limit': 100
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = dynamodb.get_user_table().scan(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            role_info = dynamodb.get_role_table().query(
                KeyConditionExpression=Key('username').eq(item['username'])
            )
            result = {
                'username': item['username'],
                'created_at': item['created_at'] if 'created_at' in item else None,
                'updated_at': item['updated_at'] if 'updated_at' in item else None,
                'email': item['email'] if 'email' in item else None
            }
            for role in role_info['Items']:
                if 'orgs' not in result:
                    result['orgs'] = []
                result['orgs'].append({'org': role['organization'], 'roles': role['roles']})
            results.append(result)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response({'items': results, 'next': headers.get('X-NEXT-KEY')}, headers=headers)


@app.route('/users', cors=True, authorizer=authorizer, methods=['POST'])
@decorator.check_json_body({
    'username': {'type': 'string', 'required': True},
    'email': {'type': 'string', 'required': True, 'empty': False}
})
@decorator.check_root_admin()
def create_new_user():
    # register to Cognito
    r = app.current_request.json_body
    user_info = dynamodb.get_user_table().get_item(Key={'username': r['username']})
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
        dynamodb.get_user_table().put_item(Item=data)
    else:
        return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs', cors=True, authorizer=authorizer, methods=['GET'])
@decorator.check_root_admin()
def organizations():
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'Limit': 100
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = dynamodb.get_org_table().scan(**args)
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

    return Response({'items': results, 'next': headers.get('X-NEXT-KEY')}, headers=headers)


@app.route('/orgs', cors=True, authorizer=authorizer, methods=['POST'])
@decorator.check_root_admin()
@decorator.check_json_body({'name': {'type': 'string', 'required': True, 'empty': False}})
def create_organization():
    r = app.current_request.json_body
    org_info = dynamodb.get_org_table().get_item(Key={'name': r['name']})
    if not 'Item' in org_info:
        ts = Decimal(time.time())
        data = {'name': r['name'], 'created_at': ts, 'updated_at': ts}
        dynamodb.get_org_table().put_item(Item=data)
        return Response(body=data, status_code=201)
    else:
        return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs/{org}', methods=['GET'], cors=True, authorizer=authorizer)
@decorator.check_org_permission('read')
def organization_info(org):
    org_info = dynamodb.get_org_table().get_item(Key={'name': org})
    if 'Item' in org_info:
        return org_info['Item']
    else:
        return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/users', methods=['POST'], cors=True, authorizer=authorizer)
@decorator.check_org_permission('admin')
@decorator.check_json_body({'username': {'type': 'string', 'required': True},
                  'roles': {'type': 'list', 'allowed': ['admin', 'read', 'write'], 'required': True}})
def invite_org_user(org):
    r = app.current_request.json_body

    user_info = dynamodb.get_user_table().get_item(Key={'username': r['username']})
    if 'Item' not in user_info:
        return Response(body={'error': 'user not found'}, status_code=400)

    response = dynamodb.get_role_table().get_item(Key={'organization': org, 'username': r['username']})
    if 'Item' not in response:
        dynamodb.get_role_table().put_item(Item={'organization': org, 'username': r['username'], 'roles': r['roles']})
        return Response({'username': r['username'], 'organization': org, 'roles': r['roles']}, status_code=201)

    return Response(body={'error': 'already taken'}, status_code=400)


@app.route('/orgs/{org}/users/{username}', methods=['DELETE'], cors=True, authorizer=authorizer)
@decorator.check_org_permission('admin')
def remove_org_user(org, username):
    response = dynamodb.get_role_table().get_item(Key={'organization': org, 'username': username})
    if 'Item' in response:
        dynamodb.get_role_table().delete_item(Key={'organization': org, 'username': username})
        return Response(body=None, status_code=204)

    return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/users/{username}', methods=['PUT'], cors=True, authorizer=authorizer)
@decorator.check_org_permission('admin')
@decorator.check_json_body({'roles': {'type': 'list', 'allowed': ['admin', 'read', 'write'], 'required': True}})
def update_org_user(org, username):
    r = app.current_request.json_body
    response = dynamodb.get_role_table().get_item(Key={'organization': org, 'username': username})
    if 'Item' in response:
        dynamodb.get_role_table().put_item(Item={'organization': org, 'username': username, 'roles': r['roles']})
        return Response({'username': username, 'organization': org, 'roles': r['roles']}, status_code=201)

    return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/users', methods=['GET'], cors=True, authorizer=authorizer)
@decorator.check_org_permission('read')
def org_users(org):
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'KeyConditionExpression': Key('organization').eq(org),
        'IndexName': 'organization_index',
        'Limit': 100
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = dynamodb.get_role_table().query(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            result = {'username': item['username'], 'roles': item['roles']}
            results.append(result)

    # bind user's information
    if len(results) > 0:
        table_name = str(os.environ.get('OTM_USER_DYNAMODB_TABLE'))
        user_info = dynamodb.client.batch_get_item(RequestItems={
            table_name: {
                'Keys': [{'username': {'S': d.get('username')}} for d in results]
            }
        })
        for user in user_info['Responses'][table_name]:
            record = [d for d in results if d['username'] == user['username']['S']][0]
            for field_key in user:
                record[field_key] = deser.deserialize(user[field_key])

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response({'items': results, 'next': headers.get('X-NEXT-KEY')}, headers=headers)


app.register_blueprint(container_routes, url_prefix='/orgs/{org}/containers')
app.register_blueprint(stats_routes, url_prefix='/orgs/{org}/containers/{name}/stats')
app.register_blueprint(usage_routes, url_prefix='/orgs/{org}/usages')
app.register_blueprint(goal_routes, url_prefix='/orgs/{org}/containers/{name}/goals')
app.register_blueprint(payment_routes, url_prefix='/orgs/{org}/payments')
app.register_blueprint(users_routes, url_prefix='/orgs/{org}/containers/{name}/users')
