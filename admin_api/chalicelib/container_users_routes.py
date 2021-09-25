from chalice import Blueprint, Response
from . import app, authorizer, athena_client, s3, execute_athena_query
from .decorator import check_org_permission, check_json_body
import os
import datetime
import json

users_routes = Blueprint(__name__)


def save_usage(org, name, execution_id, state_result):
    scanned = state_result['QueryExecution']['Statistics']['DataScannedInBytes']
    usage_key = 'org={0}/tid={1}/{2}/{3}.json'.format(org, name,
                                                      datetime.datetime.now().strftime('year=%Y/month=%-m/day=%-d'),
                                                      execution_id)
    usage_key = '{0}{1}'.format(os.environ.get('OTM_USAGE_PREFIX'), usage_key)
    s3.Object(os.environ.get('OTM_STATS_BUCKET'), usage_key).put(
        Body=json.dumps({'type': 'athena_scan', 'size': scanned}))


def users_query(org, tid, stime, etime):
    return """SELECT
JSON_EXTRACT_SCALAR(qs, '$.cid') as cid,
COUNT(qs) as c
FROM {0}
WHERE org = '{1}'
AND tid = '{2}'
AND year * 10000 + month * 100 + day >= {3}
AND year * 10000 + month * 100 + day <= {4}
AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL
AND datetime >= timestamp '{5}'
AND datetime <= timestamp '{6}'
GROUP BY JSON_EXTRACT_SCALAR(qs, '$.cid')
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


def user_query(org, tid, cid, stime, etime):
    return """SELECT datetime,
JSON_EXTRACT_SCALAR(qs, '$.o_s') AS state,
JSON_EXTRACT_SCALAR(qs, '$.dt') AS dt, 
JSON_EXTRACT_SCALAR(qs, '$.dl') AS dl, 
JSON_EXTRACT_SCALAR(qs, '$.o_psid') AS psid,
cs_user_agent
FROM {0}
WHERE org = '{1}'
AND tid = '{2}'
AND year * 10000 + month * 100 + day >= {3}
AND year * 10000 + month * 100 + day <= {4}
AND JSON_EXTRACT_SCALAR(qs, '$.o_s') IS NOT NULL
AND datetime >= timestamp '{5}'
AND datetime <= timestamp '{6}'
AND JSON_EXTRACT_SCALAR(qs, '$.cid') = '{7}'
ORDER BY  datetime DESC 
""".format(
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

    execution_id = execute_athena_query(users_query(org, name, stime, etime))
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
            save_usage(org, name, execution_id, state_result)

        # transform rows
        for row in r:
            items.append({
                'cid': row['Data'][0]['VarCharValue'],
                'c': int(row['Data'][1]['VarCharValue'])
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
    stime = int(body['stime'])
    etime = int(body['etime'])
    execution_id = execute_athena_query(user_query(org, name, cid, stime, etime))
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
            save_usage(org, name, execution_id, state_result)

        # transform rows
        for row in r:
            items.append({
                'datetime': row['Data'][0]['VarCharValue'],
                'state': row['Data'][1]['VarCharValue'] if row['Data'][1] else None,
                'dt': row['Data'][2]['VarCharValue'] if row['Data'][2] else None,
                'dl': row['Data'][3]['VarCharValue'] if row['Data'][3] else None,
                'psid': row['Data'][4]['VarCharValue'] if row['Data'][4] else None,
                'cs_user_agent': row['Data'][5]['VarCharValue'] if row['Data'][5] else None
            })

        if 'NextToken' in result:
            headers['X-NEXT-KEY'] = result['NextToken']

    # TODO: save cache

    # TODO: save usage report

    return Response({
        'state': state,
        'items': items,
        'next': headers.get('X-NEXT-KEY')
    }, headers=headers)
