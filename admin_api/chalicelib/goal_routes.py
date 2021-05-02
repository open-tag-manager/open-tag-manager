from chalice import Blueprint, Response
from . import app, authorizer, s3_client, batch_client
from .decorator import check_org_permission, check_json_body
from .dynamodb import get_container_table
import os
import uuid

goal_routes = Blueprint(__name__)

@goal_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('read')
def get_container_goals(org, name):
    container_info = get_container_table().get_item(Key={'tid': name})
    if 'Item' not in container_info:
        return Response(body={'error': 'not found'}, status_code=404)
    if not container_info['Item']['organization'] == org:
        return Response(body={'error': 'not found'}, status_code=404)
    if 'goals' not in container_info['Item']:
        return Response(body=[], status_code=200)

    bucket = os.environ.get('OTM_STATS_BUCKET')
    prefix = (os.environ.get('OTM_STATS_PREFIX') or '')
    if not org == 'root':
        prefix += org + '/'

    result = []
    for r in container_info['Item']['goals']:
        goal = r.copy()
        goal['result_url'] = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': prefix + name + '_' + r['id'] + '_goal_result.json'},
            ExpiresIn=3600,
            HttpMethod='GET'
        )
        result.append(goal)

    return result


@goal_routes.route('/', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('write')
@check_json_body({
    'name': {'type': 'string', 'required': True, 'empty': False},
    'target': {'type': 'string', 'required': True, 'empty': False},
    'target_match': {'type': 'string', 'required': False},
    'path': {'type': 'string', 'required': False, 'nullable': True},
    'path_match': {'type': 'string', 'required': False},
    'label': {'type': 'string', 'required': False, 'nullable': True},
    'label_match': {'type': 'string', 'required': False}
})
def create_container_goals(org, name):
    container_info = get_container_table().get_item(Key={'tid': name})
    if 'Item' not in container_info:
        return Response(body={'error': 'not found'}, status_code=404)
    if not container_info['Item']['organization'] == org:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    target_match = 'eq'
    if 'target_match' in body:
        target_match = body['target_match']

    path = None
    if 'path' in body:
        path = body['path']

    path_match = 'eq'
    if 'path_match' in body:
        path_match = body['path_match']

    label = None
    if 'label' in body:
        label = body['label']

    label_match = 'eq'
    if 'label_match' in body:
        label_match = body['label_match']

    goal = {
        'id': str(uuid.uuid4()),
        'name': body['name'],
        'target': body['target'],
        'target_match': target_match,
        'path': path,
        'path_match': path_match,
        'label': label,
        'label_match': label_match
    }

    if 'goals' not in container_info['Item']:
        container_info['Item']['goals'] = []
    container_info['Item']['goals'].append(goal)
    get_container_table().put_item(Item=container_info['Item'])

    return goal


@goal_routes.route('/{goal}', methods=['DELETE'], cors=True, authorizer=authorizer)
@check_org_permission('write')
def delete_container_goals(org, name, goal):
    container_info = get_container_table().get_item(Key={'tid': name})
    if 'Item' not in container_info:
        return Response(body={'error': 'not found'}, status_code=404)
    if not container_info['Item']['organization'] == org:
        return Response(body={'error': 'not found'}, status_code=404)
    if 'goals' not in container_info['Item']:
        return Response(body={'error': 'not found'}, status_code=404)

    c = list(filter(lambda x: x['id'] == goal, container_info['Item']['goals']))
    if len(c) > 0:
        container_info['Item']['goals'].remove(c[0])
        get_container_table().put_item(Item=container_info['Item'])
        return Response(body='', status_code=204)
    else:
        return Response(body={'error': 'not found'}, status_code=404)


@goal_routes.route('/{goal}/update_requests', methods=['POST'], cors=True, authorizer=authorizer)
@check_org_permission('write')
@check_json_body({
    'startdate': {'type': 'string', 'required': True, 'empty': False},
    'enddate': {'type': 'string', 'required': True, 'empty': False}
})
def update_goal_request(org, name, goal):
    request = app.current_request
    body = request.json_body

    container_info = get_container_table().get_item(Key={'tid': name})
    if 'Item' not in container_info:
        return Response(body={'error': 'not found'}, status_code=404)
    if not container_info['Item']['organization'] == org:
        return Response(body={'error': 'not found'}, status_code=404)
    if 'goals' not in container_info['Item']:
        return Response(body={'error': 'not found'}, status_code=404)

    c = list(filter(lambda x: x['id'] == goal, container_info['Item']['goals']))
    if len(c) > 0:
        job = batch_client.submit_job(
            jobName=('otm_data_retriever_' + name + '_goal_term_' + str(uuid.uuid4())),
            jobQueue=os.environ.get('STATS_BATCH_JOB_QUEUE'),
            jobDefinition=os.environ.get('STATS_BATCH_JOB_DEFINITION'),
            containerOverrides={'command': ['python', 'otmplugins/otm-goal-plugin/goal_term.py'], 'environment': [
                {'name': 'TID', 'value': name},
                {'name': 'GOAL_ID', 'value': goal},
                {'name': 'STARTDATE', 'value': body['startdate']},
                {'name': 'ENDDATE', 'value': body['enddate']}
            ]}
        )
        return Response(body={'queue': job['jobId']}, status_code=201)
    else:
        return Response(body={'error': 'not found'}, status_code=404)
