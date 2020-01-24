from chalice import Blueprint, Response
from botocore.errorfactory import ClientError
from . import authorizer, has_role, s3, get_config_data, get_container_data
import os
import json

swagger_doc_routes = Blueprint(__name__)


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


@swagger_doc_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
def get_container_swagger_doc(org, name):
    app = swagger_doc_routes._current_app
    if not has_role(app, org, 'read'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    doc = get_container_swagger_doc_data(org, name)
    if doc is None:
        return {}

    return doc


@swagger_doc_routes.route('/', methods=['PUT'], cors=True, authorizer=authorizer)
def put_container_swagger_doc(org, name):
    app = swagger_doc_routes._current_app
    if not has_role(app, org, 'write'):
        return Response(body={'error': 'permission error'}, status_code=401)

    config = get_config_data(org)
    (data, container) = get_container_data(org, name, config)

    if data is None:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    put_container_swagger_doc_data(org, name, body)
    return body
