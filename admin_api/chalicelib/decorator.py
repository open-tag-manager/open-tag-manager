from . import app, get_current_user_name
from .dynamodb import get_role_table
from chalice import Response
from boto3.dynamodb.conditions import Key
from cerberus import Validator


def has_permission(org, role):
    item = get_role_table().query(
        KeyConditionExpression=Key('username').eq(get_current_user_name())
    )
    for r in item['Items']:
        if r['organization'] == 'root' and 'admin' in r['roles']:
            return True

        if r['organization'] == org and role in r['roles']:
            return True

    return False


def check_org_permission(role):
    def __decorator(func):
        def inner(*args, **kwargs):
            org = app.current_request.uri_params['org']
            if not has_permission(org, role):
                return Response(body={'error': 'permission error'}, status_code=401)
            return func(*args, **kwargs)

        return inner

    return __decorator


def check_root_admin():
    def __decorator(func):
        def inner(*args, **kwargs):
            if not has_permission('root', 'admin'):
                return Response(body={'error': 'permission error'}, status_code=401)
            return func(*args, **kwargs)

        return inner

    return __decorator


def check_json_body(schema):
    def __decorator(func):
        def inner(*args, **kwargs):
            request = app.current_request.json_body
            if request is None:
                return Response(body={'error': 'bad request'}, status_code=400)

            v = Validator(schema)
            if v.validate(request):
                return func(*args, **kwargs)
            else:
                return Response(body={'error': 'bad request', 'error_fields': v.errors}, status_code=400)

        return inner

    return __decorator
