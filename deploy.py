import subprocess
import shutil
import json
import yaml
import bcrypt
import os
from getpass import getpass

def main():
    subprocess.call(['npm', 'run', 'build'], env={'NODE_ENV': 'production', 'PATH': os.environ.get('PATH')})
    subprocess.call(['terraform', 'apply'])

    with open('./terraform.tfstate') as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    shutil.copy('./client_apis/.chalice/config.json.sample', './client_apis/.chalice/config.json')
    shutil.copy('./client_apis/.chalice/policy-sample.json', './client_apis/.chalice/policy-dev.json')
    shutil.copy('./s3weblog2athena/config/sample.yml', './s3weblog2athena/config/dev.yml')
    shutil.copy('./athena2bigquery/config/sample.yml', './athena2bigquery/config/athena2bigquery-config.yml')
    shutil.copy('./athena2bigquery/trigger/config/sample.yml', './athena2bigquery/trigger/config/dev.yml')

    with open('./client_apis/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        if not env['ROOT_PASSWORD_HASH']:
            salt = bcrypt.gensalt(rounds=12, prefix=b'2b')
            password = getpass('Client Root Password: ')
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
            env['ROOT_PASSWORD_HASH'] = hashed_password.decode('utf-8')

        script_bucket = tfresource['aws_s3_bucket.otm_script']['primary']['id']
        script_domain = tfresource['aws_cloudfront_distribution.otm_script_distribution']['primary']['attributes']['domain_name']
        collect_domain = tfresource['aws_cloudfront_distribution.otm_collect_distribution']['primary']['attributes']['domain_name']
        dynamo_db_table = tfresource['aws_dynamodb_table.otm_session']['primary']['id']
        stat_bucket = tfresource['aws_s3_bucket.otm_stats']['primary']['id']
        config_bucket = tfresource['aws_s3_bucket.otm_config']['primary']['id']
        job_queue = tfresource['aws_batch_job_queue.otm']['primary']['id']
        job_definition = tfresource['aws_batch_job_definition.otm_data_retriever']['primary']['id']
        bq_dataset = tfresource['google_bigquery_dataset.dataset']['primary']['attributes']['dataset_id']

        env['OTM_BUCKET'] = script_bucket
        env['OTM_URL'] = 'https://%s/otm.js' % script_domain
        env['COLLECT_URL'] = 'https://%s/collect.html' % collect_domain
        env['OTM_SESSION_DYNAMODB_TABLE'] = dynamo_db_table
        env['OTM_STATS_BUCKET'] = stat_bucket
        env['OTM_STATS_PREFIX'] = 'stats/'
        env['STATS_BATCH_JOB_QUEUE'] = job_queue
        env['STATS_BATCH_JOB_DEFINITION'] = job_definition
        env['STATS_CONFIG_BUCKET'] = config_bucket
        env['STATS_GCLOUD_KEY_NAME'] = 'account.json'
        env['STATS_BQ_DATASET'] = bq_dataset
        env['STATS_BQ_TABLE_PREFIX'] = 'otm'


    repository_url = tfresource['aws_ecr_repository.otm_data_retriever']['primary']['attributes']['repository_url']

    p = subprocess.Popen(['aws', 'ecr', 'get-login', '--no-include-email'], stdout=subprocess.PIPE)
    p.wait()
    subprocess.call(p.stdout.readlines()[0].decode('utf-8').split())
    subprocess.call(['docker', 'build', '-t', 'otm-data-retriever', '.'], cwd='./data_retriever')
    subprocess.call(['docker', 'tag', 'otm-data-retriever:latest', '%s:latest' % repository_url], cwd='./data_retriever')
    subprocess.call(['docker', 'push', '%s:latest' % repository_url], cwd='./data_retriever')

    with open('./client_apis/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)

    with open('./client_apis/.chalice/policy-dev.json', 'r') as f:
        config = json.load(f)
        dynamo_db_table_arn = tfresource['aws_dynamodb_table.otm_session']['primary']['attributes']['arn']
        config['Statement'][1]['Resource'][0] = "arn:aws:s3:::%s/*" % script_bucket
        config['Statement'][1]['Resource'][1] = "arn:aws:s3:::%s" % script_bucket
        config['Statement'][2]['Resource'][0] = dynamo_db_table_arn

    with open('./client_apis/.chalice/policy-dev.json', 'w') as f:
        json.dump(config, f, indent=4)

    subprocess.call(['chalice', 'deploy', '--no-autogen-policy'], cwd='./client_apis')

    with open('./client_apis/.chalice/deployed/dev.json', 'r') as f:
        api_resource = json.load(f)

    client_bucket = tfresource['aws_s3_bucket.otm_client']['primary']['id']
    client_domain = tfresource['aws_cloudfront_distribution.otm_client_distribution']['primary']['attributes']['domain_name']
    subprocess.call(['yarn', 'install'], cwd='./client')
    subprocess.call(['npm', 'run', 'build'], env={
        'NODE_ENV': 'production',
        'PATH': os.environ.get('PATH'),
        'API_BASE_URL': api_resource['resources'][2]['rest_api_url'],
        'ASSETS_PUBLIC_PATH': "https://%s/" % client_domain,
        'BASE_PATH': ''
    }, cwd='./client')
    subprocess.call(['aws', 's3', 'sync', './client/dist/', 's3://%s/' % client_bucket, '--acl=public-read'])

    with open('./s3weblog2athena/config/dev.yml', 'r') as f:
        collect_log_bucket = tfresource['aws_s3_bucket.otm_collect_log']['primary']['id']
        sns_arn = tfresource['aws_sns_topic.otm_collect_log_topic']['primary']['id']
        config = yaml.load(f)
        config['TO_S3_BUCKET'] = collect_log_bucket
        config['TO_S3_PREFIX'] = 'cflog_transformed/'
        config['FROM_S3_BUCKET'] = collect_log_bucket
        config['SNS_ARN'] = sns_arn
        config['MODE'] = 'cloudfront'

    with open('./s3weblog2athena/config/dev.yml', 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))

    subprocess.call(['yarn', 'install'], cwd='./s3weblog2athena')
    subprocess.call(['sls', 'deploy', '--stage=dev', '--region=%s' % os.environ.get('AWS_DEFAULT_REGION')], cwd='./s3weblog2athena')

    with open('./athena2bigquery/config/athena2bigquery-config.yml', 'r') as f:
        gc_project_id = tfresource['google_bigquery_dataset.dataset']['primary']['attributes']['project']

        config = yaml.load(f)
        config['gcloud']['projectId'] = gc_project_id
        config['gcloud']['bigquery']['dataset'] = bq_dataset
        config['gcloud']['bigquery']['tableNamePrefix'] = 'otm'
        config['gcloud']['storage']['bucket'] = 'hoge'
        config['aws']['s3']['athena_result_bucket'] = config_bucket
        config['aws']['s3']['athena_result_prefix'] = 'athena/'
        config['aws']['s3']['schema_bucket'] = config_bucket
        config['aws']['s3']['schema_object'] = 'athena2bigquery-schema.json'
        config['aws']['athena']['database'] = ''
        config['aws']['athena']['table'] = ''
        config['aws']['athena']['region'] = ''
        config['partition'] = ''
        config['parser'] = {}

    with open('./athena2bigquery/config/athena2bigquery-config.yml', 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))

    subprocess.call(['aws', 's3', 'cp', './athena2bigquery/config/athena2bigquery-config.yml', 's3://%s/athena2bigquery-config.yml' % config_bucket, '--sse'])
    subprocess.call(['aws', 's3', 'cp', './athena2bigquery/config/schema.json', 's3://%s/athena2bigquery-schema.json' % config_bucket, '--sse'])

    repository_url = tfresource['aws_ecr_repository.otm_athena2bigquery']['primary']['attributes']['repository_url']
    subprocess.call(['docker', 'build', '-t', 'otm-athena2bigquery', '.'], cwd='./athena2bigquery')
    subprocess.call(['docker', 'tag', 'otm-athena2bigquery:latest', '%s:latest' % repository_url], cwd='./athena2bigquery')
    subprocess.call(['docker', 'push', '%s:latest' % repository_url], cwd='./athena2bigquery')

    # with open('./athena2bigquery/trigger/config/dev.yml', 'r') as f:
    #     job_definition = tfresource['aws_batch_job_definition.otm_athena2bigquery']['primary']['id']
    #     config = yaml.load(f)
    #     config['JOB_NAME_BASE'] = 'otm-athena2bigquery'
    #     config['JOB_QUEUE'] = job_queue
    #     config['JOB_DEFINITION'] = job_definition

    # with open('./athena2bigquery/trigger/config/dev.yml', 'w') as f:
    #     f.write(yaml.dump(config, default_flow_style=False))

    subprocess.call(['yarn', 'install'], cwd='./athena2bigquery/trigger')
    subprocess.call(['sls', 'deploy', '--stage=dev', '--region=%s' % os.environ.get('AWS_DEFAULT_REGION')], cwd='./athena2bigquery/trigger')

    print("Deployed: https://%s/" % client_domain)

if __name__ == '__main__':
    main()