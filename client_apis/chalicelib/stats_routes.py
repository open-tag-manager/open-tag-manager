from chalice import Blueprint, Response
from . import app, authorizer, s3, s3_client, batch_client, check_org_permission, get_stat_table, check_json_body
from urllib.parse import urlparse
import os
import re
import json
import datetime
import uuid
import time
from decimal import Decimal
from boto3.dynamodb.conditions import Key

stats_routes = Blueprint(__name__)


def _normalizeUrl(url):
    if url and url.lower() == 'undefined':
        return url

    if url:
        parsedurl = urlparse(url)
        return "{0}://{1}{2}".format(parsedurl.scheme, parsedurl.netloc, parsedurl.path)

    return None


def _match_url(pattern, url):
    if url is None:
        return False
    p = re.sub('\\\\{[^}]+\\\\}', '[^/]+', re.escape(pattern))
    return re.match('^' + p + '$', url)


@stats_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_container_stats(org, name):
    next_key = None
    if app.current_request.query_params and 'next' in app.current_request.query_params:
        next_key = json.loads(app.current_request.query_params['next'])

    args = {
        'KeyConditionExpression': Key('tid').eq(org + '/' + name),
        'Limit': 100,
        'ScanIndexForward': False
    }

    if next_key:
        args['ExclusiveStartKey'] = next_key

    table_response = get_stat_table().query(**args)
    results = []
    if 'Items' in table_response:
        for item in table_response['Items']:
            stat_info = item.copy()
            stat_info.pop('tid')
            stat_info['timestamp'] = str(stat_info['timestamp'])
            if stat_info['status'] == 'COMPLETE':
                stat_info['file_url'] = s3_client.generate_presigned_url(
                    'get_object', {
                        'Key': stat_info['file_key'], 'Bucket': os.environ.get('OTM_STATS_BUCKET')
                    }
                )
            results.append(stat_info)

    headers = {}
    if 'LastEvaluatedKey' in table_response:
        headers['X-NEXT-KEY'] = json.dumps(table_response['LastEvaluatedKey'])

    return Response(results, headers=headers)

@stats_routes.route('/{file}', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_container_stats_data(org, name, file):
    file_table_info = get_stat_table().get_item(Key={'tid': org + '/' + name, 'timestamp': Decimal(file)})
    if not 'Item' in file_table_info:
        return Response(body={'error': 'not found'}, status_code=404)

    file_info = file_table_info['Item']

    stat_info = file_info.copy()
    stat_info.pop('tid')
    stat_info.pop('timestamp')
    if stat_info['status'] == 'COMPLETE':
        stat_info['file_url'] = s3_client.generate_presigned_url(
            'get_object', {
                'Key': stat_info['file_key'], 'Bucket': os.environ.get('OTM_STATS_BUCKET')
            }
        )
    return stat_info


@stats_routes.route('/{file}/urls', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_container_stats_url_data(org, name, file):
    file_table_info = get_stat_table().get_item(Key={'tid': org + '/' + name, 'timestamp': Decimal(file)})

    if not 'Item' in file_table_info:
        return Response(body={'error': 'not found'}, status_code=404)

    file_info = file_table_info['Item']

    if not file_info['status'] == 'COMPLETE':
        return Response(body={'error': 'the result data had not been created yet'}, status_code=404)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    object = s3.Object(bucket, file_info['raw_file_key'])
    query_params = app.current_request.query_params
    url_filter = None

    if query_params and 'url_filter' in query_params:
        url_filter = query_params['url_filter']

    response = object.get()
    data = json.loads(response['Body'].read())

    if url_filter:
        states = []
        p_states = []
        new_result = []
        result = data['result']

        for r in result:
            url = _normalizeUrl(r['url'])
            p_url = _normalizeUrl(r['p_url'])

            if _match_url(url_filter, url) or _match_url(url_filter, p_url):
                r['url'] = url
                r['p_url'] = p_url

                dr = [r2 for r2 in new_result if
                      r2['url'] == url and r2['p_url'] == p_url and r2['state'] == r['state'] and r2['p_state'] ==
                      r['p_state']]
                if len(dr) > 0:
                    dr[0]['count'] += r['count']
                else:
                    states.append(r['state'])
                    p_states.append(r['p_state'])
                    new_result.append(r)

        diff_states = list(set(p_states) - set(states))
        for st in diff_states:
            if st is None:
                continue
            if not re.match(r'^click_', st):
                continue

            sdata = [r2 for r2 in result if r2['state'] == st]

            if len(sdata) > 0:
                dr = [r2 for r2 in new_result if r2['p_state'] == st]
                for node in dr:
                    node['p_title'] = sdata[0]['label']
                    node['p_label'] = sdata[0]['label']
                    node['p_xpath'] = sdata[0]['xpath']
                    node['p_a_id'] = sdata[0]['a_id']
                    node['p_class'] = sdata[0]['class']

        data['result'] = new_result

        if 'event_table' in data:
            del data['event_table']

    return data


@stats_routes.route('/{file}/events', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_container_stats_data_event(org, name, file):
    file_table_info = get_stat_table().get_item(Key={'tid': org + '/' + name, 'timestamp': Decimal(file)})
    if not 'Item' in file_table_info:
        return Response(body={'error': 'not found'}, status_code=404)

    file_info = file_table_info['Item']

    if not file_info['status'] == 'COMPLETE':
        return Response(body={'error': 'the result data had not been created yet'}, status_code=404)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    raw_obj = s3.Object(bucket, file_info['raw_file_key'])
    response = raw_obj.get()
    data = json.loads(response['Body'].read())

    del data['result']

    return data


@stats_routes.route('/', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('write')
@check_json_body({
    'stime': {'type': 'integer'},
    'etime': {'type': 'integer'},
    'label': {'type': 'string'}
})
def make_container_stats(org, name):
    request = app.current_request
    body = request.json_body

    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days=+1)
    yesterday = datetime.datetime(year=yesterday.year, month=yesterday.month, day=yesterday.day)
    yesterday_e = datetime.datetime(year=today.year, month=today.month, day=today.day)

    stime = str(int(yesterday.timestamp() * 1000))
    etime = str(int(yesterday_e.timestamp() * 1000))

    if body and 'stime' in body:
        stime = str(int(body['stime']))
    if body and 'etime' in body:
        etime = str(int(body['etime']))

    ts = Decimal(time.time())
    command = ['python', 'app.py', '--query-org', org, '--query-tid', name,
               '--query-stime', stime, '--query-etime', etime, '--file-key', str(ts)]

    job = batch_client.submit_job(
        jobName=('otm_data_retriever_' + name + '_stat_' + str(uuid.uuid4())),
        jobQueue=os.environ.get('STATS_BATCH_JOB_QUEUE'),
        jobDefinition=os.environ.get('STATS_BATCH_JOB_DEFINITION'),
        containerOverrides={'command': command}
    )

    item = {
        'tid': org + '/' + name,
        'timestamp': ts,
        'status': 'QUEUED',
        'label': '',
        'job_id': job['jobId'],
        'stime': int(stime),
        'etime': int(etime)
    }
    if 'label' in body:
        item['label'] = body['label']

    get_stat_table().put_item(Item=item)

    return Response(body={'queue': job['jobId']}, status_code=201)
