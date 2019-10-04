from chalice import Chalice, Response, CognitoUserPoolAuthorizer
from botocore.errorfactory import ClientError
from chalicelib import ScriptGenerator, S3Uploader
from boto3.dynamodb.conditions import Key
from urllib.parse import urlparse
import boto3
import os
import uuid
import time
import json
import copy
import re
import datetime
import random
import string

app = Chalice(app_name="open_tag_manager")
app.debug = True

dynamodb = boto3.resource('dynamodb')
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
batch_client = boto3.client('batch')

authorizer = CognitoUserPoolAuthorizer('UserPool', provider_arns=[str(os.environ.get('OTM_COGNITO_USER_POOL_ARN'))])


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


def get_role_table():
    return dynamodb.Table(str(os.environ.get('OTM_ROLE_DYNAMODB_TABLE')))


def get_roles():
    if not 'authorizer' in app.current_request.context:
        # for local test environment
        return [{'org': 'root', 'roles': ['write', 'read']}, {'org': 'sample', 'roles': ['write', 'read']}]

    username = app.current_request.context['authorizer']['claims']['cognito:username']

    item = get_role_table().query(
        KeyConditionExpression=Key('username').eq(username)
    )
    if not 'Items' in item:
        return []

    result = []
    for role in item['Items']:
        result.append({'org': role['organization'], 'roles': role['roles']})
    return result


def has_role(org, role_name):
    for role in get_roles():
        if (role['org'] == org or role['org'] == 'root') and role_name in role['roles']:
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


def get_container_swagger_doc_data(org, name):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + prefix + name + '_swagger_doc.json').get()
        return json.loads(response['Body'].read())
    except ClientError:
        return None


def put_container_swagger_doc_data(org, name, doc):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + prefix + name + '_swagger_doc.json').put(
        Body=json.dumps(doc),
        ContentType='application/json')


def put_container_data(org, name, config):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + prefix + name + '.json').put(Body=json.dumps(config),
                                                                                         ContentType='application/json')


def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


@app.route('/', cors=True, authorizer=authorizer)
def index():
    return {'success': True}


@app.route('/orgs', cors=True, authorizer=authorizer)
def organizations():
    return get_roles()


@app.route('/orgs/{org}/containers', cors=True, authorizer=authorizer)
def containers(org):
    if not has_role(org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    if not 'containers' in config:
        return []

    return config['containers']


def make_random_name(org):
    config = get_config_data(org)
    if not 'containers' in config:
        config['containers'] = []
    containers = config['containers']
    name = 'OTM-' + randomname(8).upper();
    if len(list(filter(lambda x: x['name'] == name, containers))) > 0:
        return make_random_name(org)

    return name


@app.route('/orgs/{org}/containers', methods=['POST'], cors=True, authorizer=authorizer)
def create_container(org):
    if not has_role(org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    request = app.current_request
    body = request.json_body
    if not 'name' in body:
        return Response(body={'error': 'name is required'}, status_code=400)

    config = get_config_data(org)
    if not 'containers' in config:
        config['containers'] = []
    containers = config['containers']
    if len(list(filter(lambda x: x['name'] == body['name'], containers))) > 0:
        return Response(body={'error': 'duplicated container'}, status_code=400)

    ts = int(time.time())
    new_container = {
        'name': make_random_name(org),
        'org': org,
        'label': body['name'],
        'created_at': ts,
        'updated_at': ts
    }
    config['containers'].append(new_container)
    put_config_data(org, config)

    return new_container


@app.route('/orgs/{org}/containers/{name}', cors=True, authorizer=authorizer)
def get_container(org, name):
    if not has_role(org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    return data


@app.route('/orgs/{org}/containers/{name}', methods=['PUT'], cors=True, authorizer=authorizer)
def put_container(org, name):
    if not has_role(org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body
    if not 'observers' in body or not 'triggers' in body:
        return Response(body={'error': 'there is no observer or trigger configurations'}, status_code=400)
    if not isinstance(body['observers'], list) or not isinstance(body['triggers'], list):
        return Response(body={'error': 'there is no observer configurations'}, status_code=400)

    ts = int(time.time())
    data['org'] = org
    data['updated_at'] = ts
    data['observers'] = body['observers']
    data['triggers'] = body['triggers']
    container['updated_at'] = ts

    # publish javascript
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    generator = ScriptGenerator(os.environ.get('OTM_URL'), os.environ.get('COLLECT_URL'))
    generator.import_config(data)
    script = generator.generate()
    uploader = S3Uploader(None, script_bucket=os.environ.get('OTM_BUCKET'), otm_path=os.environ.get('OTM_URL'))
    uploader.upload_script(prefix + name + '.js', script)

    data['script'] = uploader.script_url()
    if os.environ.get('OTM_SCRIPT_CDN'):
        data['script'] = uploader.script_url_cdn(os.environ.get('OTM_SCRIPT_CDN'))

    put_config_data(org, config)
    put_container_data(org, name, data)

    return data


@app.route('/orgs/{org}/containers/{name}', methods=['DELETE'], cors=True, authorizer=authorizer)
def delete_container(org, name):
    if not has_role(org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    config['containers'].remove(container)
    put_config_data(org, config)

    return Response(body='', status_code=204)


@app.route('/orgs/{org}/containers/{name}/swagger_doc', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_swagger_doc(org, name):
    if not has_role(org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    doc = get_container_swagger_doc_data(org, name)
    if doc is None:
        return {}

    return doc


@app.route('/orgs/{org}/containers/{name}/swagger_doc', methods=['PUT'], cors=True, authorizer=authorizer)
def put_container_swagger_doc(org, name):
    if not has_role(org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    put_container_swagger_doc_data(org, name, body)
    return body


@app.route('/orgs/{org}/containers/{name}/stats', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats(org, name):
    if not has_role(org, 'read'):
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


@app.route('/orgs/{org}/containers/{name}/stats/{file}', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats_data(org, name, file):
    if not has_role(org, 'read'):
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


@app.route('/orgs/{org}/containers/{name}/goals', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_goals(org, name):
    if not has_role(org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    file = (os.environ.get('OTM_STATS_PREFIX') or '') + 'goals.json'
    object = s3.Object(bucket, file)
    try:
        response = object.get()
        data = json.loads(response['Body'].read())
        result = list(filter(lambda x: x['org'] == org and x['container'] == name, data))

        return result
    except ClientError:
        return Response(body=[], status_code=200)


@app.route('/orgs/{org}/containers/{name}/goals', methods=['POST'], cors=True, authorizer=authorizer)
def create_container_goals(org, name):
    if not has_role(org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    file = (os.environ.get('OTM_STATS_PREFIX') or '') + 'goals.json'
    object = s3.Object(bucket, file)

    request = app.current_request
    body = request.json_body
    if not 'name' in body or not 'target' in body:
        return Response(body={'error': 'name or target is required'}, status_code=400)

    try:
        response = object.get()
        data = json.loads(response['Body'].read())
    except ClientError:
        data = []

    target_match = 'eq'
    if 'target_match' in body:
        target_match = body['target_match']

    path = None
    if 'path' in body:
        path = body['path']

    path_match = 'eq'
    if 'path_match' in body:
        path_match = body['path_match']

    goal = {
        'id': str(uuid.uuid4()),
        'name': body['name'],
        'org': org,
        'container': name,
        'target': body['target'],
        'target_match': target_match,
        'path': path,
        'path_match': path_match
    }
    data.append(goal)

    s3.Object(bucket, file).put(Body=json.dumps(data), ContentType='application/json')

    return goal


@app.route('/orgs/{org}/containers/{name}/goals/{goal}', methods=['DELETE'], cors=True, authorizer=authorizer)
def delete_container_goals(org, name, goal):
    if not has_role(org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    o_prefix = ''
    if org != 'root':
        o_prefix = org + '/'

    bucket = os.environ.get('OTM_STATS_BUCKET')
    file = (os.environ.get('OTM_STATS_PREFIX') or '') + 'goals.json'
    object = s3.Object(bucket, file)
    try:
        response = object.get()
        data = json.loads(response['Body'].read())
        c = list(filter(lambda x: x['id'] == goal and x['org'] == org and x['container'] == name, data))
        if len(c) > 0:
            data.remove(c[0])
            s3.Object(bucket, file).put(Body=json.dumps(data), ContentType='application/json')
            return Response(body='', status_code=204)
        else:
            return Response(body={'error': 'not found'}, status_code=404)
    except ClientError:
        return Response(body={'error': 'not found'}, status_code=404)


@app.route('/orgs/{org}/containers/{name}/stats/{file}/events', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_stats_data_event(org, name, file):
    if not has_role(org, 'read'):
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


@app.route('/orgs/{org}/containers/{name}/stats', methods=['POST'], cors=True, authorizer=authorizer)
def make_container_stats(org, name):
    if not has_role(org, 'write'):
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
