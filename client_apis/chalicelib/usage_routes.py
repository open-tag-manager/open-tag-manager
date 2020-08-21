from chalice import Blueprint, Response
from . import app, authorizer
from .dynamodb import get_usage_table
from .decorator import check_org_permission
import json
from boto3.dynamodb.conditions import Key

usage_routes = Blueprint(__name__)


@usage_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_usage(org):
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'KeyConditionExpression': Key('organization').eq(org),
        'Limit': 100,
        'ScanIndexForward': False
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = get_usage_table().query(**args)
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
