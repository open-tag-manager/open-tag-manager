from chalice import Chalice, Response
from chalicelib import ScriptGenerator, S3Uploader, authorizer, s3, get_roles, has_role, get_config_data, \
    get_container_data
from chalicelib.container_routes import container_routes
from chalicelib.swagger_doc_routes import swagger_doc_routes
from chalicelib.stats_routes import stats_routes
from botocore.errorfactory import ClientError
import importlib
import json
import os

app = Chalice(app_name="open_tag_manager")
app.debug = True
app.experimental_feature_flags.update(['BLUEPRINTS'])


@app.route('/', cors=True, authorizer=authorizer)
def index():
    return {'success': True}


@app.route('/orgs', cors=True, authorizer=authorizer)
def organizations():
    return get_roles(app)


@app.route('/orgs/{org}', methods=['GET'], cors=True, authorizer=authorizer)
def organization_info(org):
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)
    freezed_orgs = []
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').get()
        freezed_orgs = json.loads(response['Body'].read())
    except ClientError:
        pass

    return {'org': org, 'freezed': org in freezed_orgs}


@app.route('/orgs/{org}/freeze', methods=['POST'], cors=True, authorizer=authorizer)
def organization_freeze(org):
    if not has_role(app, 'root', 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    freezed_orgs = []
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').get()
        freezed_orgs = json.loads(response['Body'].read())
    except ClientError:
        pass

    if not org in freezed_orgs:
        freezed_orgs.append(org)

    # remove all container script
    config = get_config_data(org)
    if config:
        for c in config['containers']:
            prefix = ''
            if org != 'root':
                prefix = org + '/'

            try:
                s3.Object(os.environ.get('OTM_BUCKET'), prefix + c['name'] + '.js').delete()
            except ClientError:
                pass

    # save freezed data
    s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').put(Body=json.dumps(freezed_orgs),
                                                                ContentType='application/json')

    return Response(body='', status_code=204)


@app.route('/orgs/{org}/unfreeze', methods=['POST'], cors=True, authorizer=authorizer)
def organization_unfreeze(org):
    if not has_role(app, 'root', 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    freezed_orgs = []
    try:
        response = s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').get()
        freezed_orgs = json.loads(response['Body'].read())
    except ClientError:
        pass

    if org in freezed_orgs:
        freezed_orgs.remove(org)
    else:
        return Response(body={'error': 'org is not freezed'}, status_code=401)

    prefix = ''
    if org != 'root':
        prefix = org + '/'

    # re-deploy container script
    config = get_config_data(org)
    if config:
        for c in config['containers']:
            (data, container) = get_container_data(org, c['name'], config)
            generator = ScriptGenerator(os.environ.get('OTM_URL'), os.environ.get('COLLECT_URL'))
            generator.import_config(data)
            script = generator.generate()
            uploader = S3Uploader(None, script_bucket=os.environ.get('OTM_BUCKET'), otm_path=os.environ.get('OTM_URL'))
            uploader.upload_script(prefix + c['name'] + '.js', script)

    # save freezed data
    s3.Object(os.environ.get('OTM_BUCKET'), 'freezed.json').put(Body=json.dumps(freezed_orgs),
                                                                ContentType='application/json')

    return Response(body='', status_code=204)


app.register_blueprint(container_routes, url_prefix='/orgs/{org}/containers')
app.register_blueprint(swagger_doc_routes, url_prefix='/orgs/{org}/containers/{name}/swagger_doc')
app.register_blueprint(stats_routes, url_prefix='/orgs/{org}/containers/{name}/stats')

plugins = json.loads(os.environ.get('OTM_PLUGINS'), encoding='utf-8')
for plugin in plugins:
    module = importlib.import_module('chalicelib.otmplugins.' + plugin['package'] + '.' + plugin['module'])
    app.register_blueprint(module.plugin_app, url_prefix=plugin['urlPrefix'])
