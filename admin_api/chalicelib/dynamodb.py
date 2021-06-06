import boto3
import os

resource = boto3.resource('dynamodb')
client = boto3.client('dynamodb')


def get_role_table():
    return resource.Table(str(os.environ.get('OTM_ROLE_DYNAMODB_TABLE')))


def get_user_table():
    return resource.Table(str(os.environ.get('OTM_USER_DYNAMODB_TABLE')))


def get_org_table():
    return resource.Table(str(os.environ.get('OTM_ORG_DYNAMODB_TABLE')))


def get_stat_table():
    return resource.Table(str(os.environ.get('OTM_STAT_DYNAMODB_TABLE')))


def get_container_table():
    return resource.Table(str(os.environ.get('OTM_CONTAINER_DYNAMODB_TABLE')))


def get_usage_table():
    return resource.Table(str(os.environ.get('OTM_USAGE_DYNAMODB_TABLE')))
