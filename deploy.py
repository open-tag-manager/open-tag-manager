import subprocess
import shutil
import json
import os
import re
import glob
import time


def main():
    environment = os.environ.get('ENV') or 'dev'
    s_environment = os.environ.get('S_ENV') or 'shared'
    region = os.environ.get('AWS_DEFAULT_REGION')
    backend_bucket = os.environ.get('TERRAFORM_BACKEND_BUCKET')
    backend_region = os.environ.get('TERRAFORM_BACKEND_REGION') or region

    print('1. deploy infra')

    terraform_init_cmd = ['terraform', 'init',
                          '-backend-config=bucket=%s' % backend_bucket,
                          '-backend-config=key=aws-batch',
                          '-backend-config=region=%s' % backend_region]

    print('1.1. deploy shared infra')
    subprocess.run(terraform_init_cmd, cwd='./infra/aws-batch', check=True)
    subprocess.run(['terraform', 'workspace', 'new', s_environment], cwd='./infra/aws-batch', check=False)
    subprocess.run(['terraform', 'workspace', 'select', s_environment], cwd='./infra/aws-batch', check=True)

    terraform_apply_cmd = ['terraform', 'plan']
    if os.path.exists('terraform.tfvars'):
        terraform_apply_cmd.append('-var-file=%s' % '../../terraform.tfvars')

    subprocess.run(terraform_apply_cmd, cwd='./infra/aws-batch', check=True)

    terraform_apply_cmd[1] = 'apply'
    if not os.environ.get('CONFIRM'):
        terraform_apply_cmd.append('-auto-approve')

    subprocess.run(terraform_apply_cmd, cwd='./infra/aws-batch', check=True)
    shared_infra = subprocess.run(['terraform', 'show', '-json'], stdout=subprocess.PIPE, cwd='./infra/aws-batch',
                                  check=True)
    shared_infra_result = json.loads(shared_infra.stdout.decode('utf8'))['values']['root_module']['resources']
    job_queue = [x for x in shared_infra_result if x['address'] == 'aws_batch_job_queue.otm'][0]['values']['arn']

    print('1.2. deploy infra')

    terraform_init_cmd[3] = '-backend-config=key=common'
    subprocess.run(terraform_init_cmd, cwd='./infra/common', check=True)
    subprocess.run(['terraform', 'workspace', 'new', environment], cwd='./infra/common', check=False)
    subprocess.run(['terraform', 'workspace', 'select', environment], cwd='./infra/common', check=True)

    terraform_apply_cmd = [
        'terraform', 'plan',
        '-var=aws_batch_job_queue_arn=%s' % job_queue,
        '-var=aws_region=%s' % region
    ]
    if os.path.exists('terraform.tfvars'):
        terraform_apply_cmd.append('-var-file=%s' % '../../terraform.tfvars')
    if os.path.exists('%s-terraform.tfvars' % environment):
        terraform_apply_cmd.append('-var-file=../../%s-terraform.tfvars' % environment)

    subprocess.run(terraform_apply_cmd, cwd='./infra/common', check=True)

    terraform_apply_cmd[1] = 'apply'
    if not os.environ.get('CONFIRM'):
        terraform_apply_cmd.append('-auto-approve')

    subprocess.run(terraform_apply_cmd, cwd='./infra/common', check=True)
    common_result = subprocess.run(['terraform', 'show', '-json'], stdout=subprocess.PIPE, cwd='./infra/common',
                                   check=True)

    # parse terraform result
    common_resources = json.loads(common_result.stdout.decode('utf8'))['values']['root_module']['resources']

    script_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_script'][0]['values']['bucket']
    client_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_client'][0]['values']['bucket']
    stat_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_stats'][0]['values']['bucket']
    config_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_config'][0]['values']['bucket']
    athena_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_athena'][0]['values']['bucket']
    collect_log_bucket = [x for x in common_resources if x['address'] == 'aws_s3_bucket.otm_collect_log'][0]['values']['bucket']

    script_distribution_values = [x for x in common_resources if x['address'] == 'aws_cloudfront_distribution.otm_script_distribution'][0]['values']
    script_distribution = script_distribution_values['id']
    script_domain = script_distribution_values['domain_name']
    if script_distribution_values['aliases'] and len(script_distribution_values['aliases']) > 0:
        script_domain = script_distribution_values['aliases'][0]

    collect_distribution_values = [x for x in common_resources if x['address'] == 'aws_cloudfront_distribution.otm_collect_distribution'][0]['values']
    collect_domain = collect_distribution_values['domain_name']
    if collect_distribution_values['aliases'] and len(collect_distribution_values['aliases']) > 0:
        collect_domain = collect_distribution_values['aliases'][0]

    client_distribution_values = [x for x in common_resources if x['address'] == 'aws_cloudfront_distribution.otm_client_distribution'][0]['values']
    client_distribution = client_distribution_values['id']
    client_domain = client_distribution_values['domain_name']
    if client_distribution_values['aliases'] and len(client_distribution_values['aliases']) > 0:
        client_domain = client_distribution_values['aliases'][0]

    dynamo_role_values = [x for x in common_resources if x['address'] == 'aws_dynamodb_table.otm_role'][0]['values']
    dynamo_role_table = dynamo_role_values['id']
    dynamo_role_table_arn = dynamo_role_values['arn']

    dynamo_org_values = [x for x in common_resources if x['address'] == 'aws_dynamodb_table.otm_org'][0]['values']
    dynamo_org_table = dynamo_org_values['id']
    dynamo_org_table_arn = dynamo_org_values['arn']

    dynamo_user_values = [x for x in common_resources if x['address'] == 'aws_dynamodb_table.otm_user'][0]['values']
    dynamo_user_table = dynamo_user_values['id']
    dynamo_user_table_arn = dynamo_user_values['arn']

    dynamo_container_values = [x for x in common_resources if x['address'] == 'aws_dynamodb_table.otm_container'][0]['values']
    dynamo_container_table = dynamo_container_values['id']
    dynamo_container_table_arn = dynamo_container_values['arn']

    dynamo_usage_values = [x for x in common_resources if x['address'] == 'aws_dynamodb_table.otm_usage'][0]['values']
    dynamo_usage_table = dynamo_usage_values['id']
    dynamo_usage_table_arn = dynamo_usage_values['arn']

    job_definition = [x for x in common_resources if x['address'] == 'aws_batch_job_definition.otm_data_retriever'][0]['values']['id']

    sns_topic = [x for x in common_resources if x['address'] == 'aws_sns_topic.otm_collect_log_topic'][0]['values']['name']

    athena_database = [x for x in common_resources if x['address'] == 'aws_glue_catalog_database.otm'][0]['values']['id']

    cognito_identify_pool_values = [x for x in common_resources if x['address'] == 'aws_cognito_identity_pool.otm'][0]['values']
    cognito_identify_pool_id = cognito_identify_pool_values['id']
    aws_id = re.match('^arn:aws:cognito-identity:[a-z0-9\-]+:([0-9]+):identitypool', cognito_identify_pool_values['arn'])[1]
    cognito_identity_provider = cognito_identify_pool_values['cognito_identity_providers'][0]
    cognito_user_pool_client_id = cognito_identity_provider['client_id']
    cognito_user_pool_id = re.match('^cognito-idp\.([a-z0-9\-]+)\.amazonaws.com/(.+)$', cognito_identity_provider['provider_name'])[2]
    cognito_user_pool_arn = 'arn:aws:cognito-idp:%s:%s:userpool/%s' % (
        region, aws_id, cognito_user_pool_id)

    repository_url = [x for x in common_resources if x['address'] == 'aws_ecr_repository.otm_data_retriever'][0]['values']['repository_url']

    shutil.copy('./admin_api/.chalice/config.json.sample', './admin_api/.chalice/config.json')
    shutil.copy('./log_formatter/.chalice/config.json.sample', './log_formatter/.chalice/config.json')

    print('2. deploy otm.js')
    subprocess.run(['yarn', 'install'], cwd='./collector', check=True)
    subprocess.run(['npm', 'run', 'build'], cwd='./collector', env={'NODE_ENV': 'production', 'PATH': os.environ.get('PATH')}, check=True)
    subprocess.run(['aws', 's3', 'cp', './collector/dist/otm.js', 's3://%s/otm.js' % script_bucket, '--acl=public-read'],
                   check=True)

    print('3. deploy client API')
    with open('./admin_api/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        env['OTM_BUCKET'] = script_bucket
        env['OTM_URL'] = 'https://%s/otm.js' % script_domain
        env['COLLECT_URL'] = 'https://%s/collect' % collect_domain
        env['OTM_ROLE_DYNAMODB_TABLE'] = dynamo_role_table
        env['OTM_USER_DYNAMODB_TABLE'] = dynamo_user_table
        env['OTM_ORG_DYNAMODB_TABLE'] = dynamo_org_table
        env['OTM_CONTAINER_DYNAMODB_TABLE'] = dynamo_container_table
        env['OTM_USAGE_DYNAMODB_TABLE'] = dynamo_usage_table
        env['OTM_STATS_BUCKET'] = stat_bucket
        env['OTM_STATS_PREFIX'] = 'stats/'
        env['OTM_USAGE_PREFIX'] = 'usage/'
        env['OTM_SCRIPT_CDN'] = 'https://%s' % script_domain
        env['OTM_COGNITO_USER_POOL_ARN'] = cognito_user_pool_arn
        env['STATS_BATCH_JOB_QUEUE'] = job_queue
        env['STATS_BATCH_JOB_DEFINITION'] = job_definition
        env['STATS_CONFIG_BUCKET'] = config_bucket
        env['STATS_GCLOUD_KEY_NAME'] = 'account.json'
        env['STATS_ATHENA_DATABASE'] = athena_database
        env['STATS_ATHENA_TABLE'] = 'otm_collect'
        env['STATS_ATHENA_RESULT_BUCKET'] = athena_bucket

    with open('./admin_api/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)

    with open('./admin_api/.chalice/policy-sample.json', 'r') as f:
        config = json.load(f)
        config['Statement'][1]['Resource'] = []
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % script_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % script_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % stat_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % stat_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % athena_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % athena_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % collect_log_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % collect_log_bucket)
        config['Statement'][2]['Resource'] = []
        config['Statement'][2]['Resource'].append(dynamo_role_table_arn)
        config['Statement'][2]['Resource'].append(dynamo_role_table_arn + '/*')
        config['Statement'][2]['Resource'].append(dynamo_user_table_arn)
        config['Statement'][2]['Resource'].append(dynamo_user_table_arn + '/*')
        config['Statement'][2]['Resource'].append(dynamo_org_table_arn)
        config['Statement'][2]['Resource'].append(dynamo_org_table_arn + '/*')
        config['Statement'][2]['Resource'].append(dynamo_container_table_arn)
        config['Statement'][2]['Resource'].append(dynamo_container_table_arn + '/*')
        config['Statement'][2]['Resource'].append(dynamo_usage_table_arn)
        config['Statement'][2]['Resource'].append(dynamo_usage_table_arn + '/*')
        config['Statement'][3]['Resource'] = []
        config['Statement'][3]['Resource'].append(cognito_user_pool_arn)

    with open('./admin_api/.chalice/policy-%s.json' % environment, 'w') as f:
        json.dump(config, f, indent=4)

    subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd='./admin_api', check=True)
    subprocess.run(['chalice', 'deploy', '--no-autogen-policy', '--stage=%s' % environment], cwd='./admin_api',
                   check=True)

    print('4. deploy data_retriever')

    p = subprocess.Popen(['aws', 'ecr', 'get-login', '--no-include-email'], stdout=subprocess.PIPE)
    p.wait()
    subprocess.run(p.stdout.readlines()[0].decode('utf-8').split(), check=True)
    subprocess.run(['docker', 'build', '-t', 'otm-data-retriever', '.'], cwd='./data_retriever', check=True)
    subprocess.run(['docker', 'tag', 'otm-data-retriever:latest', '%s:latest' % repository_url], cwd='./data_retriever',
                   check=True)
    subprocess.run(['docker', 'push', '%s:latest' % repository_url], cwd='./data_retriever', check=True)

    print('5. deploy client frontend')
    with open('./admin_api/.chalice/deployed/%s.json' % environment, 'r') as f:
        api_resource = json.load(f)

    subprocess.run(['yarn', 'install'], cwd='./admin_client', check=True)

    with open('./admin_client/.env', 'w') as f:
        f.write('AWS_DEFAULT_REGION=%s\n' % region)
        f.write('COGNITO_IDENTITY_POOL_ID=%s\n' % cognito_identify_pool_id)
        f.write('COGNITO_USER_POOL_ID=%s\n' % cognito_user_pool_id)
        f.write('COGNITO_USER_POOL_WEB_CLIENT_ID=%s\n' % cognito_user_pool_client_id)

    client_build_env = {
        'NODE_ENV': 'production',
        'PATH': os.environ.get('PATH'),
        'API_BASE_URL': api_resource['resources'][3]['rest_api_url'],
        'COGNITO_IDENTITY_POOL_ID': cognito_identify_pool_id,
        'AWS_DEFAULT_REGION': region,
        'COGNITO_USER_POOL_ID': cognito_user_pool_id,
        'COGNITO_USER_POOL_WEB_CLIENT_ID': cognito_user_pool_client_id,
        'COGNITO_COOKIE_STORAGE_DOMAIN': client_domain,
        'COGNITO_COOKIE_SECURE': '1',
        'OTM_OTM_URL': os.environ.get('OTM_OTM_URL') or '',
        'OTM_HEAD_SCRIPT': os.environ.get('OTM_HEAD_SCRIPT') or '',
        'OTM_HEAD_NOSCRIPT': os.environ.get('OTM_HEAD_NOSCRIPT') or ''
    }

    subprocess.run(['yarn', 'run', 'build'], env=client_build_env, cwd='./admin_client', check=True)
    subprocess.run(['aws', 's3', 'sync', './admin_client/dist/', 's3://%s/' % client_bucket, '--acl=public-read'], check=True)

    print('6. invalidate client / otm.js')
    subprocess.run(
        ['aws', 'cloudfront', 'create-invalidation', '--distribution-id', script_distribution, '--paths', '/otm.js'],
        check=True)
    subprocess.run(
        ['aws', 'cloudfront', 'create-invalidation', '--distribution-id', client_distribution, '--paths', '/',
         '/index.html'], check=True)

    print('7. deploy log_formatter')
    with open('./log_formatter/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        env['OTM_REFORM_S3_BUCKET'] = collect_log_bucket
        env['OTM_REFORM_LOG_PREFIX'] = 'formatted/'
        env['OTM_STAT_S3_BUCKET'] = stat_bucket
        env['OTM_STAT_LOG_PREFIX'] = 'usage/'

    with open('./log_formatter/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)

    with open('./log_formatter/.chalice/policy-sample.json', 'r') as f:
        config = json.load(f)
        config['Statement'][1]['Resource'] = []
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % collect_log_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % collect_log_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s/*' % stat_bucket)
        config['Statement'][1]['Resource'].append('arn:aws:s3:::%s' % stat_bucket)

    with open('./log_formatter/.chalice/policy-%s.json' % environment, 'w') as f:
        json.dump(config, f, indent=4)

    subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd='./log_formatter', check=True)
    local_env = os.environ.copy()
    local_env['OTM_LOG_SNS'] = sns_topic
    subprocess.run(['chalice', 'deploy', '--no-autogen-policy', '--stage=%s' % environment], cwd='./log_formatter',
                   env=local_env, check=True)

    print('8. add seed data')
    ts = str(int(time.time()))
    print('8.1. org data')
    subprocess.run([
        'aws',
        'dynamodb',
        'update-item',
        '--table-name',
        dynamo_org_table,
        '--key',
        json.dumps({'name': {'S': 'root'}}),
        '--update-expression',
        'SET created_at = if_not_exists(created_at, :c), updated_at = if_not_exists(updated_at, :u)',
        '--expression-attribute-values',
        json.dumps({':c': {'N': ts}, ':u': {'N': ts}})
    ], check=True)

    print('8.2. user data')
    if os.environ.get('ROOT_EMAIL'):
        idp_result = subprocess.run([
            'aws',
            'cognito-idp',
            'admin-get-user',
            '--user-pool-id',
            cognito_user_pool_id,
            '--username',
            'root'
        ], check=False)
        if idp_result.returncode == 255:
            print('create idp user')
            subprocess.run([
                'aws',
                'cognito-idp',
                'admin-create-user',
                '--user-pool-id',
                cognito_user_pool_id,
                '--username',
                'root',
                '--user-attributes',
                'Name=email,Value=%s' % os.environ.get('ROOT_EMAIL'),
                'Name=email_verified,Value=true'
            ], check=True)
        subprocess.run([
            'aws',
            'dynamodb',
            'update-item',
            '--table-name',
            dynamo_user_table,
            '--key',
            json.dumps({'username': {'S': 'root'}}),
            '--update-expression',
            'SET created_at = if_not_exists(created_at, :c), updated_at = if_not_exists(updated_at, :u), email = :e',
            '--expression-attribute-values',
            json.dumps({':c': {'N': str(int(time.time()))},
                        ':u': {'N': str(int(time.time()))},
                        ':e': {'S': os.environ.get('ROOT_EMAIL')}})
        ], check=True)
        subprocess.run([
            'aws',
            'dynamodb',
            'update-item',
            '--table-name',
            dynamo_role_table,
            '--key',
            json.dumps({'username': {'S': 'root'}, 'organization': {'S': 'root'}}),
            '--update-expression',
            'SET #r = if_not_exists(#r, :r)',
            '--expression-attribute-names',
            json.dumps({'#r': 'roles'}),
            '--expression-attribute-values',
            json.dumps({':r': {'L': [{'S': 'read'}, {'S': 'write'}, {'S': 'admin'}]}})
        ], check=True)
    else:
        print('Skip to add user data because ROOT_EMAIL is blank')

    print("Deployed: https://%s/" % client_domain)


if __name__ == '__main__':
    main()
