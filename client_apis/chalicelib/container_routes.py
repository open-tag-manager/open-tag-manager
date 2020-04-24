from chalice import Blueprint, Response
from . import ScriptGenerator, S3Uploader, s3, authorizer, get_config_data, has_role, put_config_data, \
    get_container_data
from botocore.errorfactory import ClientError
import string
import random
import time
import os
import json

container_routes = Blueprint(__name__)


def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def make_random_name(org):
    config = get_config_data(org)
    if not 'containers' in config:
        config['containers'] = []
    containers = config['containers']
    name = 'OTM-' + randomname(8).upper();
    if len(list(filter(lambda x: x['name'] == name, containers))) > 0:
        return make_random_name(org)

    return name


def put_container_data(org, name, config):
    prefix = ''
    if org != 'root':
        prefix = org + '/'

    s3.Object(os.environ.get('OTM_BUCKET'), 'containers/' + prefix + name + '.json').put(Body=json.dumps(config),
                                                                                         ContentType='application/json')


@container_routes.route('/', cors=True, methods=['GET'], authorizer=authorizer)
def containers(org):
    app = container_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    if not 'containers' in config:
        return []

    return config['containers']


@container_routes.route('/', cors=True, methods=['POST'], authorizer=authorizer)
def create_container(org):
    app = container_routes._current_app
    if not has_role(app, org, 'write'):
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
        'updated_at': ts,
        'domains': []
    }
    config['containers'].append(new_container)
    put_config_data(org, config)

    return new_container


@container_routes.route('/{name}', cors=True, methods=['GET'], authorizer=authorizer)
def get_container(org, name):
    app = container_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    return data


@container_routes.route('/{name}', methods=['PUT'], cors=True, authorizer=authorizer)
def put_container(org, name):
    app = container_routes._current_app
    if not has_role(app, org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body
    ts = int(time.time())
    data['org'] = org

    if 'observers' in body:
        if not isinstance(body['observers'], list):
            return Response(body={'error': 'observers should set by array'}, status_code=400)
        data['observers'] = body['observers']

    if 'triggers' in body:
        if not isinstance(body['triggers'], list):
            return Response(body={'error': 'triggers should set by array'}, status_code=400)
        data['triggers'] = body['triggers']

    if 'label' in body and body['label']:
        container['label'] = data['label'] = body['label']

    if 'domains' in body:
        if not isinstance(body['domains'], list):
            return Response(body={'error': 'domains should set by array'}, status_code=400)
        container['domains'] = data['domains'] = body['domains']

    container['updated_at'] = ts
    data['updated_at'] = ts

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


@container_routes.route('/{name}', methods=['DELETE'], cors=True, authorizer=authorizer)
def delete_container(org, name):
    app = container_routes._current_app
    if not has_role(app, org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    prefix = ''
    if org != 'root':
        prefix = org + '/'

    try:
        s3.Object(os.environ.get('OTM_BUCKET'), prefix + name + '.js').delete()
    except ClientError:
        pass

    config['containers'].remove(container)
    put_config_data(org, config)

    return Response(body='', status_code=204)
