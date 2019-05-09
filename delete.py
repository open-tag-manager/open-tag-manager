import subprocess
import json
import os
import sys


def main():
    environment = os.environ.get('ENV') or 'dev'
    s_environment = os.environ.get('S_ENV') or 'shared'

    while True:
        i = input('Remove OTM? [Y/n]:')
        if i == 'Y':
            break
        elif i == 'n':
            sys.exit(1)

    if not os.path.exists('./infra/aws-batch/terraform.tfstate.d/' + s_environment):
        sys.stderr.write('shared environment not found.')
        sys.exit(1)
    if not os.path.exists('./infra/common/terraform.tfstate.d/' + environment):
        sys.stderr.write('environment not found.')
        sys.exit(1)

    with open('./infra/aws-batch/terraform.tfstate.d/{0}/terraform.tfstate'.format(s_environment)) as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    job_queue = tfresource['aws_batch_job_queue.otm']['primary']['id']

    with open('./infra/common/terraform.tfstate.d/{0}/terraform.tfstate'.format(environment)) as f:
        tfstate = json.load(f)
        tfresource = tfstate['modules'][0]['resources']

    client_bucket = tfresource['aws_s3_bucket.otm_client']['primary']['id']

    athena_bucket = tfresource['aws_s3_bucket.otm_athena']['primary']['id']
    athena_database = tfresource['aws_athena_database.otm']['primary']['id']

    print('1. delete athena table')
    athena_query = 'DROP TABLE IF EXISTS {0}.otm_collect2'.format(athena_database)
    subprocess.call([
        'aws',
        'athena',
        'start-query-execution',
        '--query-string',
        athena_query,
        '--result-configuration',
        'OutputLocation=s3://%s/deploy' % athena_bucket
    ])

    print('2. delete log_formatter')
    subprocess.call(['chalice', 'delete', '--stage={0}'.format(environment)], cwd='./log_formatter')

    print('3. delete client frontend')
    subprocess.call(['aws', 's3', 'rm', 's3://{0}'.format(client_bucket), '--recursive'])

    print('4. delete client API')
    subprocess.call(['chalice', 'delete', '--stage={0}'.format(environment)], cwd='./client_apis')

    print('5. delete infra')

    print('5.1. delete common infra')
    subprocess.call(['terraform', 'workspace', 'select', environment], cwd='./infra/common')
    vars = ['terraform', 'destroy', '-var-file=../../terraform.tfvars',
            '-var=aws_batch_job_queue_arn={0}'.format(job_queue)]
    if os.path.exists('{0}-terraform.tfvars'.format(environment)):
        vars.append('-var-file=../../{0}-terraform.tfvars'.format(environment))
    subprocess.call(vars, cwd='./infra/common')

    print('5.2. delete common infra')
    while True:
        i = input('Remove Shared Infra (AWS Batch) ? [Y/n]:')
        if i == 'Y':
            break
        elif i == 'n':
            sys.exit(1)

    subprocess.call(['terraform', 'workspace', 'select', s_environment], cwd='./infra/aws-batch')
    subprocess.call(['terraform', 'destroy', '-var-file=../../terraform.tfvars'], cwd='./infra/aws-batch')


if __name__ == '__main__':
    main()
