import subprocess
import shutil
import json
import bcrypt
import os
from getpass import getpass

def main():
    # subprocess.call(['npm', 'run', 'build'], env={'NODE_ENV': 'production', 'PATH': os.environ.get('PATH')})
    # subprocess.call(['terraform', 'apply'])

    with open('./terraform.tfstate') as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    shutil.copy('./client_apis/.chalice/config.json.sample', './client_apis/.chalice/config.json')
    shutil.copy('./client_apis/.chalice/policy-sample.json', './client_apis/.chalice/policy-dev.json')

    with open('./client_apis/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        if not env['ROOT_PASSWORD_HASH']:
            salt = bcrypt.gensalt(rounds=12, prefix=b'2b')
            password = getpass('Password: ')
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
    print("Deployed: https://%s/" % client_domain)

if __name__ == '__main__':
    main()