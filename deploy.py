import subprocess
import shutil
import json
import yaml
import bcrypt
import os
from getpass import getpass

def main():
    environment = os.environ.get('ENV') or 'dev'
    s_environment = os.environ.get('S_ENV') or 'shared'

    print('1. deploy infra')
    subprocess.call(['npm', 'run', 'build'], env={'NODE_ENV': 'production', 'PATH': os.environ.get('PATH')})

    print('1.1. deploy shared infra')
    subprocess.call(['terraform', 'init'], cwd='./infra/aws-batch')
    if not os.path.exists('./infra/aws-batch/terraform.tfstate.d/%s' % s_environment):
        subprocess.call(['terraform', 'workspace', 'new', s_environment], cwd='./infra/aws-batch')
    subprocess.call(['terraform', 'workspace', 'select', s_environment], cwd='./infra/aws-batch')
    subprocess.call(['terraform', 'apply', '-var-file=../../terraform.tfvars'], cwd='./infra/aws-batch')

    print('1.2. deploy infra')

    with open('./infra/aws-batch/terraform.tfstate.d/%s/terraform.tfstate' % s_environment) as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    job_queue = tfresource['aws_batch_job_queue.otm']['primary']['id']

    subprocess.call(['terraform', 'init'], cwd='./infra/common')
    if not os.path.exists('./infra/common/terraform.tfstate.d/' + environment):
        subprocess.call(['terraform', 'workspace', 'new', environment], cwd='./infra/common')
    subprocess.call(['terraform', 'workspace', 'select', environment], cwd='./infra/common')
    vars = ['terraform', 'apply', '-var-file=../../terraform.tfvars',
            '-var=aws_batch_job_queue_arn=%s' % job_queue]
    if os.path.exists('%s-terraform.tfvars' % environment):
        vars.append('-var-file=../../%s-terraform.tfvars' % environment)
    subprocess.call(vars, cwd='./infra/common')

    with open('./infra/common/terraform.tfstate.d/%s/terraform.tfstate' % environment) as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    script_bucket = tfresource['aws_s3_bucket.otm_script']['primary']['id']
    client_bucket = tfresource['aws_s3_bucket.otm_client']['primary']['id']
    stat_bucket = tfresource['aws_s3_bucket.otm_stats']['primary']['id']
    config_bucket = tfresource['aws_s3_bucket.otm_config']['primary']['id']
    athena_bucket = tfresource['aws_s3_bucket.otm_athena']['primary']['id']
    collect_log_bucket = tfresource['aws_s3_bucket.otm_collect_log']['primary']['id']

    script_domain = tfresource['aws_cloudfront_distribution.otm_script_distribution']['primary']['attributes']['domain_name']
    if 'aws_route53_record.otm' in tfresource:
        script_domain = tfresource['aws_route53_record.otm']['primary']['attributes']['name']

    collect_domain = tfresource['aws_cloudfront_distribution.otm_collect_distribution']['primary']['attributes']['domain_name']
    if 'aws_route53_record.collect' in tfresource:
        collect_domain = tfresource['aws_route53_record.collect']['primary']['attributes']['name']

    client_domain = tfresource['aws_cloudfront_distribution.otm_client_distribution']['primary']['attributes']['domain_name']
    if 'aws_route53_record.client' in tfresource:
        client_domain = tfresource['aws_route53_record.client']['primary']['attributes']['name']

    dynamo_db_table = tfresource['aws_dynamodb_table.otm_session']['primary']['id']
    dynamo_db_table_arn = tfresource['aws_dynamodb_table.otm_session']['primary']['attributes']['arn']

    job_definition = tfresource['aws_batch_job_definition.otm_data_retriever']['primary']['id']

    gc_project_id = tfresource['google_bigquery_dataset.dataset']['primary']['attributes']['project']
    bq_dataset = tfresource['google_bigquery_dataset.dataset']['primary']['attributes']['dataset_id']
    gc_storage = tfresource['google_storage_bucket.bucket']['primary']['attributes']['id']

    sns_arn = tfresource['aws_sns_topic.otm_collect_log_topic']['primary']['id']

    athena_database = tfresource['aws_athena_database.otm']['primary']['id']

    shutil.copy('./client_apis/.chalice/config.json.sample', './client_apis/.chalice/config.json')
    shutil.copy('./client_apis/.chalice/policy-sample.json', './client_apis/.chalice/policy-dev.json')
    shutil.copy('./s3weblog2athena/config/sample.yml', './s3weblog2athena/config/dev.yml')
    shutil.copy('./athena2bigquery/config/sample.yml', './athena2bigquery/config/athena2bigquery-config.yml')
    shutil.copy('./athena2bigquery/trigger/config/sample.yml', './athena2bigquery/trigger/config/dev.yml')

    print('2. deploy client API')
    with open('./client_apis/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        if not env['ROOT_PASSWORD_HASH']:
            salt = bcrypt.gensalt(rounds=12, prefix=b'2b')
            password = getpass('Client Root Password: ')
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
            env['ROOT_PASSWORD_HASH'] = hashed_password.decode('utf-8')

        env['OTM_BUCKET'] = script_bucket
        env['OTM_URL'] = 'https://%s/otm.js' % script_domain
        env['COLLECT_URL'] = 'https://%s/collect.html' % collect_domain
        env['OTM_SESSION_DYNAMODB_TABLE'] = dynamo_db_table
        env['OTM_STATS_BUCKET'] = stat_bucket
        env['OTM_STATS_PREFIX'] = 'stats/'
        env['OTM_SCRIPT_CDN'] = 'https://%s' % script_domain
        env['STATS_BATCH_JOB_QUEUE'] = job_queue
        env['STATS_BATCH_JOB_DEFINITION'] = job_definition
        env['STATS_CONFIG_BUCKET'] = config_bucket
        env['STATS_GCLOUD_KEY_NAME'] = 'account.json'
        env['STATS_BQ_DATASET'] = bq_dataset
        env['STATS_BQ_TABLE_PREFIX'] = 'otm'

    with open('./client_apis/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)

    with open('./client_apis/.chalice/policy-sample.json', 'r') as f:
        config = json.load(f)
        config['Statement'][1]['Resource'] = []
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % script_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % script_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % stat_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % stat_bucket)
        config['Statement'][2]['Resource'][0] = dynamo_db_table_arn

    with open('./client_apis/.chalice/policy-%s.json' % environment, 'w') as f:
        json.dump(config, f, indent=4)

    subprocess.call(['pip', 'install', '-r', 'requirements.txt'], cwd='./client_apis')
    subprocess.call(['chalice', 'deploy', '--no-autogen-policy', '--stage=%s' % environment], cwd='./client_apis')

    print('3. deploy data_retriever')
    repository_url = tfresource['aws_ecr_repository.otm_data_retriever']['primary']['attributes']['repository_url']
    p = subprocess.Popen(['aws', 'ecr', 'get-login', '--no-include-email'], stdout=subprocess.PIPE)
    p.wait()
    subprocess.call(p.stdout.readlines()[0].decode('utf-8').split())
    subprocess.call(['docker', 'build', '-t', 'otm-data-retriever', '.'], cwd='./data_retriever')
    subprocess.call(['docker', 'tag', 'otm-data-retriever:latest', '%s:latest' % repository_url], cwd='./data_retriever')
    subprocess.call(['docker', 'push', '%s:latest' % repository_url], cwd='./data_retriever')

    print('4. deploy client frontend')
    with open('./client_apis/.chalice/deployed/%s.json' % environment, 'r') as f:
        api_resource = json.load(f)

    subprocess.call(['yarn', 'install'], cwd='./client')
    subprocess.call(['npm', 'run', 'build'], env={
        'NODE_ENV': 'production',
        'PATH': os.environ.get('PATH'),
        'API_BASE_URL': api_resource['resources'][2]['rest_api_url'],
        'ASSETS_PUBLIC_PATH': "https://%s/" % client_domain,
        'BASE_PATH': ''
    }, cwd='./client')
    subprocess.call(['aws', 's3', 'sync', './client/dist/', 's3://%s/' % client_bucket, '--acl=public-read'])

    print('5. deploy s3weblog2athena')
    with open('./s3weblog2athena/config/sample.yml', 'r') as f:
        config = yaml.load(f)
        config['TO_S3_BUCKET'] = collect_log_bucket
        config['TO_S3_PREFIX'] = 'cflog_transformed/'
        config['FROM_S3_BUCKET'] = collect_log_bucket
        config['SNS_ARN'] = sns_arn
        config['MODE'] = 'cloudfront'

    with open('./s3weblog2athena/config/%s.yml' % environment, 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))

    subprocess.call(['yarn', 'install'], cwd='./s3weblog2athena')
    subprocess.call(['sls', 'deploy', '--stage=%s' % environment, '--region=%s' % os.environ.get('AWS_DEFAULT_REGION')], cwd='./s3weblog2athena')

    print('6. deploy athena2bigquery')
    with open('./athena2bigquery/config/athena2bigquery-config.yml', 'r') as f:
        config = yaml.load(f)
        config['gcloud']['projectId'] = gc_project_id
        config['gcloud']['bigquery']['dataset'] = bq_dataset
        config['gcloud']['bigquery']['tableNamePrefix'] = 'otm'
        config['gcloud']['storage']['bucket'] = gc_storage
        config['aws']['s3']['athena_result_bucket'] = athena_bucket
        config['aws']['s3']['athena_result_prefix'] = ''
        config['aws']['s3']['schema_bucket'] = config_bucket
        config['aws']['s3']['schema_object'] = 'athena2bigquery-schema.json'
        config['aws']['athena']['database'] = athena_database
        config['aws']['athena']['table'] = 'otm_collect'
        config['aws']['athena']['region'] = os.environ.get('AWS_DEFAULT_REGION')
        config['log_type'] = 'cloudfront'
        config['partition'] = ''
        config['parser'] = {
            'queryToJson': {
                'qs_json': {
                    'target': 'cs_uri_query'
                }
            }
        }

    with open('./athena2bigquery/config/athena2bigquery-config.yml', 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))

    subprocess.call(['aws', 's3', 'cp', './athena2bigquery/config/athena2bigquery-config.yml', 's3://%s/athena2bigquery-config.yml' % config_bucket, '--sse'])
    subprocess.call(['aws', 's3', 'cp', './athena2bigquery/config/schema_cf.json', 's3://%s/athena2bigquery-schema.json' % config_bucket, '--sse'])

    repository_url = tfresource['aws_ecr_repository.otm_athena2bigquery']['primary']['attributes']['repository_url']
    subprocess.call(['docker', 'build', '-t', 'otm-athena2bigquery', '.'], cwd='./athena2bigquery')
    subprocess.call(['docker', 'tag', 'otm-athena2bigquery:latest', '%s:latest' % repository_url], cwd='./athena2bigquery')
    subprocess.call(['docker', 'push', '%s:latest' % repository_url], cwd='./athena2bigquery')

    athena_query = '''
CREATE EXTERNAL TABLE IF NOT EXISTS %s.otm_collect (
  `date` string,
  `time` string,
  `x_edge_location` string,
  `sc_bytes` string,
  `c_ip` string,
  `cs_method` string,
  `cs_host` string,
  `cs_uri_stem` string,
  `cs_status` string,
  `cs_referer` string,
  `cs_user_agent` string,
  `cs_uri_query` string,
  `cs_cookie` string,
  `cs_x_edge_result_type` string,
  `cs_x_edge_request_id` string,
  `x_host_header` string,
  `cs_protocol` string,
  `cs_bytes` string,
  `time_taken` string,
  `x_forwarded_for` string,
  `ssl_protocol` string,
  `ssl_cipher` string,
  `x_edge_response_result_type` string,
  `cs_protocol_version` string,
  `fle_status` string,
  `fle_encrypted_fields` string
) PARTITIONED BY (
  year int,
  month int,
  day int
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = '	',
  'field.delim' = '	'
) LOCATION 's3://%s/cflog_transformed/'
TBLPROPERTIES ('has_encrypted_data'='false');
''' % (athena_database, collect_log_bucket)

    subprocess.call([
        'aws',
        'athena',
        'start-query-execution',
        '--query-string',
        athena_query,
        '--result-configuration',
        'OutputLocation=s3://%s/deploy' % athena_bucket
    ])

    print("Deployed: https://%s/" % client_domain)

if __name__ == '__main__':
    main()
