from chalice import Chalice, Response
from botocore.errorfactory import ClientError
from chalicelib import ScriptGenerator, S3Uploader
import bcrypt
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


def get_session_table():
    return dynamodb.Table(str(os.environ.get('OTM_SESSION_DYNAMODB_TABLE')))


def get_session():
    request = app.current_request
    if not 'Authorization' in request.headers:
        return None
    item = get_session_table().get_item(Key={
        'session_id': request.headers['Authorization']
    })
    if not 'Item' in item:
        return None

    return item['Item']


def get_config_data():
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'config.json').get()
        return json.loads(response['Body'].read())
    except ClientError:
        return {}


def put_config_data(config):
    s3.Object(os.environ.get('OTM_BUCKET'), 'config.json').put(Body=json.dumps(config), ContentType='application/json')


def get_container_data(name, config):
    containers = config['containers']
    c = list(filter(lambda x: x['name'] == name, containers))
    if len(c) <= 0:
        return (None, None)

    container = c[0]
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + name + '.json').get()
        return (json.loads(response['Body'].read()), container)
    except ClientError:
        return (copy.copy(container), container)


def get_container_swagger_doc_data(name):
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + name + '_swagger_doc.json').get()
        print(response)
        return json.loads(response['Body'].read())
    except ClientError:
        return None


def put_container_swagger_doc_data(name, doc):
    s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + name + '_swagger_doc.json').put(Body=json.dumps(doc),
                                                                                            ContentType='application/json')


def put_container_data(name, config):
    s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + name + '.json').put(Body=json.dumps(config),
                                                                                ContentType='application/json')


def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


@app.route("/", cors=True)
def index():
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    return {'username': session['username']}


@app.route('/containers', cors=True)
def containers():
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    if not 'containers' in config:
        return []

    return config['containers']


def make_random_name():
    config = get_config_data()
    if not 'containers' in config:
        config['containers'] = []
    containers = config['containers']
    name = 'OTM-' + randomname(8).upper();
    if len(list(filter(lambda x: x['name'] == name, containers))) > 0:
        return make_random_name()

    return name


@app.route('/containers', methods=['POST'], cors=True)
def create_container():
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    request = app.current_request
    body = request.json_body
    if not 'name' in body:
        return Response(body={'error': 'name is required'}, status_code=400)

    config = get_config_data()
    if not 'containers' in config:
        config['containers'] = []
    containers = config['containers']
    if len(list(filter(lambda x: x['name'] == body['name'], containers))) > 0:
        return Response(body={'error': 'duplicated container'}, status_code=400)

    ts = int(time.time())
    new_container = {
        'name': make_random_name(),
        'label': body['name'],
        'created_at': ts,
        'updated_at': ts
    }
    config['containers'].append(new_container)
    put_config_data(config)

    return new_container


@app.route('/containers/{name}', cors=True)
def get_container(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    return data


@app.route('/containers/{name}', methods=['PATCH'], cors=True)
def put_container(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body
    if not 'observers' in body or not 'triggers' in body:
        return Response(body={'error': 'there is no observer or trigger configurations'}, status_code=400)
    if not isinstance(body['observers'], list) or not isinstance(body['triggers'], list):
        return Response(body={'error': 'there is no observer configurations'}, status_code=400)

    ts = int(time.time())
    data['updated_at'] = ts
    data['observers'] = body['observers']
    data['triggers'] = body['triggers']
    container['updated_at'] = ts

    # publish javascript
    generator = ScriptGenerator(os.environ.get('OTM_URL'), os.environ.get('COLLECT_URL'))
    generator.import_config(data)
    script = generator.generate()
    uploader = S3Uploader(None, script_bucket=os.environ.get('OTM_BUCKET'), otm_path=os.environ.get('OTM_URL'))
    uploader.upload_script(name + '.js', script)

    data['script'] = uploader.script_url()
    if os.environ.get('OTM_SCRIPT_CDN'):
        data['script'] = uploader.script_url_cdn(os.environ.get('OTM_SCRIPT_CDN'))

    put_config_data(config)
    put_container_data(name, data)

    return data


@app.route('/containers/{name}', methods=['DELETE'], cors=True)
def delete_container(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    config['containers'].remove(container)
    put_config_data(config)

    return Response(body='', status_code=204)


@app.route('/containers/{name}/swagger_doc', methods=['GET'], cors=True)
def get_container_swagger_doc(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    doc = get_container_swagger_doc_data(name)
    if doc is None:
        return Response(body={}, status_code=404)

    return doc


@app.route('/containers/{name}/swagger_doc', methods=['PUT'], cors=True)
def put_container_swagger_doc(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    put_container_swagger_doc_data(name, body)
    return body


@app.route('/containers/{name}/stats', methods=['GET'], cors=True)
def get_container_stats(name):
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    prefix = (os.environ.get('OTM_STATS_PREFIX') or '') + name + '/'
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


@app.route('/containers/{name}/stats', methods=['POST'], cors=True)
def make_container_stats(name):
    request = app.current_request
    body = request.json_body
    session = get_session()
    if not session:
        return Response(body={'error': 'session required'}, status_code=401)

    config = get_config_data()
    (data, container) = get_container_data(name, config)

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

    command = [
        '-c',
        os.environ.get('STATS_CONFIG_BUCKET'),
        '-k',
        os.environ.get('STATS_GCLOUD_KEY_NAME'),
        '-d',
        os.environ.get('STATS_BQ_DATASET'),
        '-p',
        os.environ.get('STATS_BQ_TABLE_PREFIX'),
        '-t',
        os.environ.get('OTM_STATS_BUCKET'),
        '-n',
        (os.environ.get('OTM_STATS_PREFIX') or '') + name + '/',
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


@app.route("/login", methods=['POST'], cors=True)
def login():
    request = app.current_request
    body = request.json_body
    if not 'username' in body or not 'password' in body:
        return Response(body={'error': 'login error'}, status_code=400)

    username = ''

    if body['username'] == 'root' and bcrypt.checkpw(body['password'].encode('utf-8'),
                                                     os.environ.get('ROOT_PASSWORD_HASH').encode('utf-8')):
        username = body['username']

    if username:
        token = str(uuid.uuid4())
        get_session_table().put_item(
            Item={
                'session_id': token,
                'username': username,
                'created_at': int(time.time())
            }
        )

        return {'username': username, 'token': token}

    return Response(body={'error': 'login error'}, status_code=400)
