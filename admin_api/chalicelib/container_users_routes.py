from chalice import Blueprint, Response
from . import app, authorizer, athena_client, execute_athena_query, save_athena_usage_report
from .dynamodb import get_container_table
from .decorator import check_org_permission, check_json_body
import os
import datetime

users_routes = Blueprint(__name__)


def users_query(org, tid, stime, etime):
    return """SELECT
JSON_EXTRACT_SCALAR(qs, '$.cid') as cid,
JSON_EXTRACT_SCALAR(qs, '$.uid') as uid,
COUNT(qs) as c
FROM {0}
WHERE org = '{1}'
AND tid = '{2}'
AND year * 10000 + month * 100 + day >= {3}
AND year * 10000 + month * 100 + day <= {4}
AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL
AND datetime >= timestamp '{5}'
AND datetime <= timestamp '{6}'
GROUP BY JSON_EXTRACT_SCALAR(qs, '$.cid'),
JSON_EXTRACT_SCALAR(qs, '$.uid')
ORDER BY c DESC
""".format(
        os.environ.get('STATS_ATHENA_TABLE'),
        org,
        tid,
        datetime.datetime.utcfromtimestamp(stime / 1000).strftime('%Y%m%d'),
        datetime.datetime.utcfromtimestamp(etime / 1000).strftime('%Y%m%d'),
        datetime.datetime.utcfromtimestamp(stime / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        datetime.datetime.utcfromtimestamp(etime / 1000).strftime('%Y-%m-%d %H:%M:%S'),
    )


def user_query(org, tid, cid, stime, etime, hash_key):
    return """SELECT datetime,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS dt, 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS dl, 
JSON_EXTRACT_SCALAR(qs, '$.o_psid') AS psid,
JSON_EXTRACT_SCALAR(qs, '$.uid') AS uid,
JSON_EXTRACT_SCALAR(qs, '$.uhash') AS uhash,
TO_HEX(hmac_sha256(TO_UTF8(JSON_EXTRACT_SCALAR(qs, '$.uid')), TO_UTF8('{0}'))) = upper(JSON_EXTRACT_SCALAR(qs, '$.uhash')) as is_verified,
cs_user_agent
FROM {1}
WHERE org = '{2}'
AND tid = '{3}'
AND year * 10000 + month * 100 + day >= {4}
AND year * 10000 + month * 100 + day <= {5}
AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL
AND datetime >= timestamp '{6}'
AND datetime <= timestamp '{7}'
AND JSON_EXTRACT_SCALAR(qs, '$.cid') = '{8}'
ORDER BY  datetime DESC 
""".format(
        hash_key or '',
        os.environ.get('STATS_ATHENA_TABLE'),
        org,
        tid,
        datetime.datetime.utcfromtimestamp(stime / 1000).strftime('%Y%m%d'),
        datetime.datetime.utcfromtimestamp(etime / 1000).strftime('%Y%m%d'),
        datetime.datetime.utcfromtimestamp(stime / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        datetime.datetime.utcfromtimestamp(etime / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        cid
    )


def get_next_key():
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = app.current_request.query_params['next']
    return next_key


def athena_result_args(execution_id, next_key=None):
    args = {'QueryExecutionId': execution_id}
    if next_key:
        args['NextToken'] = next_key
    return args


@users_routes.route('/start_query', cors=True, methods=['POST'], authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    # measurement start time (Unix Timestamp)
    'stime': {'type': 'integer', 'required': True},
    # measurement end time (Unix Timestamp)
    'etime': {'type': 'integer', 'required': True}
})
def container_users_start_query(org, name):
    request = app.current_request
    body = request.json_body

    stime = int(body['stime'])
    etime = int(body['etime'])

    execution_id = execute_athena_query(users_query(org, name, stime, etime), token='user')
    return {'execution_id': execution_id}


@users_routes.route('/query_result/{execution_id}', cors=True, methods=['GET'], authorizer=authorizer)
@check_org_permission('read')
def container_users(org, name, execution_id):
    next_key = get_next_key()
    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id
    )
    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    items = []
    headers = {}
    if state == 'SUCCEEDED':
        args = athena_result_args(execution_id, next_key=next_key)
        result = athena_client.get_query_results(**args)

        rows = result['ResultSet']['Rows']
        r = rows
        if not next_key:
            r = rows[1:]
            save_athena_usage_report(org, name, state_result)

        # transform rows
        for row in r:
            items.append({
                'cid': row['Data'][0]['VarCharValue'],
                'uid': None if not row['Data'][1] else row['Data'][1]['VarCharValue'],
                'c': int(row['Data'][2]['VarCharValue'])
            })

        if 'NextToken' in result:
            headers['X-NEXT-KEY'] = result['NextToken']

    return Response({
        'state': state,
        'items': items,
        'next': headers.get('X-NEXT-KEY')
    }, headers=headers)


@users_routes.route('/{cid}/start_query', cors=True, methods=['POST'], authorizer=authorizer)
@check_org_permission('read')
@check_json_body({
    # measurement start time (Unix Timestamp)
    'stime': {'type': 'integer', 'required': True},
    # measurement end time (Unix Timestamp)
    'etime': {'type': 'integer', 'required': True}
})
def container_user_start_query(org, name, cid):
    request = app.current_request
    body = request.json_body
    container_info = get_container_table().get_item(Key={'tid': name})
    if not 'Item' in container_info:
        return Response(body={'error': 'not found'}, status_code=404)

    hash_key = None
    if 'hash_key' in container_info:
        hash_key = container_info['hash_key']

    stime = int(body['stime'])
    etime = int(body['etime'])
    execution_id = execute_athena_query(user_query(org, name, cid, stime, etime, hash_key), token='user_detail')
    return {'execution_id': execution_id}


@users_routes.route('/{cid}/query_result/{execution_id}', cors=True, methods=['GET'], authorizer=authorizer)
@check_org_permission('read')
def container_users(org, name, cid, execution_id):
    next_key = get_next_key()
    state_result = athena_client.get_query_execution(
        QueryExecutionId=execution_id
    )
    # QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
    state = state_result['QueryExecution']['Status']['State']
    items = []
    headers = {}
    if state == 'SUCCEEDED':
        args = athena_result_args(execution_id, next_key=next_key)
        result = athena_client.get_query_results(**args)
        rows = result['ResultSet']['Rows']
        r = rows
        if not next_key:
            r = rows[1:]
            save_athena_usage_report(org, name, state_result)

        # transform rows
        for row in r:
            items.append({
                'datetime': row['Data'][0]['VarCharValue'],
                'state': row['Data'][1]['VarCharValue'] if row['Data'][1] else None,
                'dt': row['Data'][2]['VarCharValue'] if row['Data'][2] else None,
                'dl': row['Data'][3]['VarCharValue'] if row['Data'][3] else None,
                'psid': row['Data'][4]['VarCharValue'] if row['Data'][4] else None,
                'uid': row['Data'][5]['VarCharValue'] if row['Data'][5] else None,
                'uhash': row['Data'][6]['VarCharValue'] if row['Data'][6] else None,
                'is_verified': row['Data'][7]['VarCharValue'] if row['Data'][7] else False,
                'cs_user_agent': row['Data'][8]['VarCharValue'] if row['Data'][8] else None,
            })

        if 'NextToken' in result:
            headers['X-NEXT-KEY'] = result['NextToken']

    return Response({
        'state': state,
        'items': items,
        'next': headers.get('X-NEXT-KEY')
    }, headers=headers)
