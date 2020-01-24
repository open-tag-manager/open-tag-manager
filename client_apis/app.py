from chalice import Chalice
from chalicelib import authorizer, get_roles
from chalicelib.container_routes import container_routes
from chalicelib.swagger_doc_routes import swagger_doc_routes
from chalicelib.stats_routes import stats_routes
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


app.register_blueprint(container_routes, url_prefix='/orgs/{org}/containers')
app.register_blueprint(swagger_doc_routes, url_prefix='/orgs/{org}/containers/{name}/swagger_doc')
app.register_blueprint(stats_routes, url_prefix='/orgs/{org}/containers/{name}/stats')

plugins = json.loads(os.environ.get('OTM_PLUGINS'), encoding='utf-8')
for plugin in plugins:
    module = importlib.import_module('chalicelib.otmplugins.' + plugin['package'] + '.' + plugin['module'])
    app.register_blueprint(module.app, url_prefix=plugin['urlPrefix'])
