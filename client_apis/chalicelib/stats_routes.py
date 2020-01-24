from chalice import Blueprint, Response
from botocore.errorfactory import ClientError
from . import authorizer, s3, s3_client, batch_client, has_role, get_container_data, get_config_data
from urllib.parse import urlparse
import os
import re
import json
import datetime

stats_routes = Blueprint(__name__)


def _normalizeUrl(url):
    if url and url.lower() == 'undefined':
        return url

    if url:
        parsedurl = urlparse(url)
        return "{0}://{1}{2}".format(parsedurl.scheme, parsedurl.netloc, parsedurl.path)

    return None


def _match_url(pattern, url):
    p = re.sub('\\\\{[^}]+\\\\}', '[^/]+', re.escape(pattern))
    return re.match('^' + p + '$', url)


@stats_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats(org, name):
    app = stats_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    o_prefix = ''
    if org != 'root':
        o_prefix = org + '/'

    bucket = os.environ.get('OTM_STATS_BUCKET')
    prefix = (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + name + '/'
    response = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
    result = []
    contents = []
    if 'Contents' in response:
        contents = response['Contents']

    for content in reversed(contents):
        url = s3_client.generate_presigned_url('get_object', {'Key': content['Key'], 'Bucket': bucket})
        file_name = re.match(r'^(.*/)?(.*)', content['Key'])[2]
        result.append({'url': url, 'key': content['Key'], 'name': file_name})

    return result


@stats_routes.route('/{file}', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats_data(org, name, file):
    app = stats_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    o_prefix = ''
    if org != 'root':
        o_prefix = org + '/'

    bucket = os.environ.get('OTM_STATS_BUCKET')
    prefix = (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + name + '_raw/'
    object = s3.Object(bucket, prefix + file)
    query_params = app.current_request.query_params
    url_filter = None

    if query_params and 'url_filter' in query_params:
        url_filter = query_params['url_filter']

    try:
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
    except ClientError:
        return Response(body={'error': 'not found'}, status_code=404)


@stats_routes.route('/{file}/events', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats_data_event(org, name, file):
    app = stats_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    o_prefix = ''
    if org != 'root':
        o_prefix = org + '/'

    bucket = os.environ.get('OTM_STATS_BUCKET')
    prefix = (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + name + '_raw/'
    object = s3.Object(bucket, prefix + file)
    try:
        response = object.get()
        data = json.loads(response['Body'].read())

        del data['result']

        return data
    except ClientError:
        return Response(body={'error': 'not found'}, status_code=404)


@stats_routes.route('/', methods=['POST'], cors=True, authorizer=authorizer)
def make_container_stats(org, name):
    app = stats_routes._current_app
    if not has_role(app, org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    request = app.current_request
    body = request.json_body

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

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

    o_prefix = ''
    if org != 'root':
        o_prefix = org + '/'

    command = [
        '-d',
        os.environ.get('STATS_ATHENA_DATABASE'),
        '-p',
        os.environ.get('STATS_ATHENA_TABLE'),
        '-t',
        os.environ.get('OTM_STATS_BUCKET'),
        '-n',
        (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + name + '/',
        '-r',
        (os.environ.get('OTM_STATS_PREFIX') or '') + o_prefix + name + '_raw/',
        '--result-bucket',
        os.environ.get('STATS_ATHENA_RESULT_BUCKET'),
        '--query-tid',
        name,
        '--query-stime',
        stime,
        '--query-etime',
        etime
    ]

    if body and 'label' in body:
        command.append('--target-suffix')
        command.append(body['label'])

    job = batch_client.submit_job(
        jobName=('otm_data_retriever_' + name + '_stat_' + str(uuid.uuid4())),
        jobQueue=os.environ.get('STATS_BATCH_JOB_QUEUE'),
        jobDefinition=os.environ.get('STATS_BATCH_JOB_DEFINITION'),
        containerOverrides={'command': command}
    )

    return Response(body={'queue': job['jobId']}, status_code=201)
