from chalice import Blueprint, Response
from . import app, ScriptGenerator, S3Uploader, s3, authorizer
from .dynamodb import get_container_table
from .decorator import check_org_permission, check_json_body
from botocore.errorfactory import ClientError
import string
import random
import time
import os
import json
from boto3.dynamodb.conditions import Key
from decimal import Decimal

container_routes = Blueprint(__name__)


def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def make_random_name():
    name = 'OTM-' + randomname(8).upper()
    return name


@container_routes.route('/', cors=True, methods=['GET'], authorizer=authorizer)
@check_org_permission('read')
def containers(org):
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

    table_response = get_container_table().query(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            d = item.copy()
            d.pop('organization')
            results.append(d)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response({'items': results, 'next': headers.get('X-NEXT-KEY')}, headers=headers)


@container_routes.route('/', cors=True, methods=['POST'], authorizer=authorizer)
@check_org_permission('write')
@check_json_body({
    'label': {'type': 'string', 'required': True, 'empty': False}
})
def create_container(org):
    request = app.current_request
    body = request.json_body
    ts = Decimal(time.time())
    new_container = {
        'tid': make_random_name(),
        'organization': org,
        'label': body['label'],
        'created_at': ts,
        'updated_at': ts,
        'observers': [],
        'triggers': [],
        'domains': [],
        'swagger_doc': {}
    }

    get_container_table().put_item(Item=new_container)
    return new_container


@container_routes.route('/{name}', cors=True, methods=['GET'], authorizer=authorizer)
@check_org_permission('read')
def get_container(org, name):
    container_info = get_container_table().get_item(Key={'tid': name})
    if 'Item' in container_info:
        if not container_info['Item']['organization'] == org:
            return Response(body={'error': 'not found'}, status_code=404)

        return container_info['Item']
    else:
        return Response(body={'error': 'not found'}, status_code=404)


@container_routes.route('/{name}', methods=['PUT'], cors=True, authorizer=authorizer)
@check_json_body({
    'label': {'type': 'string', 'required': False, 'empty': False},
    'observers': {'type': 'list', 'required': False, 'schema': {'type': 'dict'}},
    'triggers': {'type': 'list', 'required': False, 'schema': {'type': 'dict'}},
    'domains': {'type': 'list', 'required': False, 'schema': {'type': 'string'}},
    'swagger_doc': {'type': 'dict', 'required': False}
})
@check_org_permission('write')
def put_container(org, name):
    container_info = get_container_table().get_item(Key={'tid': name})
    if not 'Item' in container_info:
        return Response(body={'error': 'not found'}, status_code=404)

    current_container = container_info['Item']

    if not current_container['organization'] == org:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    ts = Decimal(time.time())
    current_container['updated_at'] = ts
    if 'observers' in body:
        current_container['observers'] = body['observers']
    if 'triggers' in body:
        current_container['triggers'] = body['triggers']
    if 'domains' in body:
        current_container['domains'] = body['domains']
    if 'label' in body:
        current_container['label'] = body['label']
    if 'swagger_doc' in body:
        current_container['swagger_doc'] = body['swagger_doc']

    # publish javascript
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    generator = ScriptGenerator(os.environ.get('OTM_URL'), os.environ.get('COLLECT_URL'))
    generator.import_config(current_container)
    script = generator.generate()
    uploader = S3Uploader(None, script_bucket=os.environ.get('OTM_BUCKET'), otm_path=os.environ.get('OTM_URL'))
    uploader.upload_script(prefix + name + '.js', script)

    current_container['script'] = uploader.script_url()
    if os.environ.get('OTM_SCRIPT_CDN'):
        current_container['script'] = uploader.script_url_cdn(os.environ.get('OTM_SCRIPT_CDN'))

    get_container_table().put_item(Item=current_container)

    return current_container


@container_routes.route('/{name}', methods=['DELETE'], cors=True, authorizer=authorizer)
@check_org_permission('write')
def delete_container(org, name):
    container_info = get_container_table().get_item(Key={'tid': name})
    if not 'Item' in container_info:
        return Response(body={'error': 'not found'}, status_code=404)

    prefix = ''
    if org != 'root':
        prefix = org + '/'

    try:
        s3.Object(os.environ.get('OTM_BUCKET'), prefix + name + '.js').delete()
    except ClientError:
        pass

    get_container_table().delete_item(Key={'tid': name})

    return Response(body='', status_code=204)
