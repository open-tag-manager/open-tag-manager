# Open Tag Manager

## (0) What is this

Open Tag Manager (OTM for short) is OpenSource Tag Manager and Action Tracker. You can reach raw data.

Copyright 2018-2020 Alexander Keith

This software is licensed under the Aapche Licens, Version 2.0.
Please see the file called LICENSE.


## (1) Installation

### System Requirement

- AWS: This product is using following stack.
    - CloudFront: for tracker, to distribute scripts and client web apps.
    - S3: to store scripts, logs, stat data, terraform backend and client web apps.
    - Athena: to retrieve summary data from S3 log object.
    - API Gateway / Lambda: to provide management APIs for client web apps.
    - Amazon Cognito: to manage admin users for client web apps.
    - Dynamo DB: to manage admin users roles.
    - AWS Batch: to retrieve analytics data from Athena.
    - Route 53 (Optional): to manage domains for OTM application stacks.
- docker: It's required to deploy application.

### Deploy with AWS CodeBuild

By this way, you can deploy OTM environment easily.

Firstly, you need make Amazon Cognito user pool to manage administrator.
And get the user pool id and client id.

And make a S3 bucket for terraform backend.

Go to CodeBuild console, and create new project.

- Source provider: You can set this repository as public repository.
- Environment: Use `Managed image`
    - Operation system: `Ubuntu`
    - Runtime(s): `Standard`
    - Image: `aws/codebuild/standard:4.0`
    - Image version: `Always use the latest image for this runtime version`
    - Environment type: `Linux`
    - Privileged: To build docker image, set `true`
    - Service role: Set service role that is attached `AdministratorAccess`
    - Environment variables: Set following variables
        - `AWS_DEFAULT_REGION` (Required): Your AWS region.
        - `TERRAFORM_BACKEND_BUCKET` (Required): Terraform backend S3 bucket.
        - `ROOT_EMAIL` (Optional): Default root user e-mail address.
        If not set, the deployment script will not make default user.
        - `TF_VAR_aws_s3_bucket_prefix` (Required): Bucket prefix for your S3 bucket. It can prevent name conflict. 
        Set the unique name by the project.
        - `TF_VAR_aws_cognito_user_pool_id` (Required): AWS Cognito user pool ID.
        - `TF_VAR_aws_cognito_user_pool_client_id` (Required): AWS Cognito user pool client ID.
        - `TF_VAR_aws_resource_tags` (Optional, Map): Attached tags for OTM related resources.
        - `OTM_PLUGINS` (Optional): OTM Plugin git repository URLs. Separated by space.
        - `TF_VAR_aws_cloudfront_collect_domain` (Optional, Array): tracker domain.
        - `TF_VAR_aws_cloudfront_collect_acm_certificate_arn`: ACM certification's ARN for tacker.
        - `TF_VAR_aws_route53_collect_zone_id`: tracker's domain Zone ID for Route53.
        - `TF_VAR_aws_cloudfront_otm_domain` (Optional, Array): script distributor domain.
        - `TF_VAR_aws_cloudfront_otm_acm_certificate_arn`: ACM certification's ARN for script distributor.
        - `TF_VAR_aws_route53_otm_zone_id`: script distributor's domain Zone ID for Route53.
        - `TF_VAR_aws_cloudfront_client_domain` (Optional, Array): client web apps domain.
        - `TF_VAR_aws_cloudfront_client_acm_certificate_arn`: ACM certification's ARN for client.
        - `TF_VAR_aws_route53_client_zone_id`: client's domain Zone ID for Route53.
- Artifacts:
    - Type: Set `No artifacts`
    - Additional configuration:
        - Cache type: Set `Local`, and select `Docker layer cache` and `Source cache` as local cache option.

After the build, you can get URL for client (admin) console screen.

### Deploy on local environment

Firstly, you need make Amazon Cognito user pool to manage administrator.
And get the user pool id and client id.

Copy `terraform.tfvars.sample` to `terraform.tfvars` and set your configuration.

- `aws_profile`: Your AWS profiles that managed by AWS CLI.
- `aws_region`: Your AWS region.
- `aws_s3_bucket_prefix`: Bucket prefix for your S3 bucket.
- `aws_cognito_user_pool_id`: AWS Cognito user pool ID.
- `aws_cognito_user_pool_client_id`: AWS Cognito user pool client ID.
- `aws_sources_tags` (Optional, Map): Attached tags for OTM related resources.

(Optional) If you need to attach domain for OTM related service,
create `${env}-terraform.tfvars`.

The domain should be managed by Route53.

- `aws_cloudfront_collect_domain` (Array): tracker domain.
- `aws_cloudfront_collect_acm_certificate_arn`: ACM certification's ARN for tacker.
- `aws_route53_collect_zone_id`: tracker's domain Zone ID for Route53.
- `aws_cloudfront_otm_domain` (Array): script distributor domain.
- `aws_cloudfront_otm_acm_certificate_arn`: ACM certification's ARN for script distributor.
- `aws_route53_otm_zone_id`: script distributor's domain Zone ID for Route53.
- `aws_cloudfront_client_domain` (Array): client web apps domain.
- `aws_cloudfront_client_acm_certificate_arn`: ACM certification's ARN for client.
- `aws_route53_client_zone_id`: client's domain Zone ID for Route53.

example:

```
aws_cloudfront_collect_domain = ["collect.example.com"]
aws_cloudfront_collect_acm_certificate_arn = "arn:aws:acm:us-east-1:xxx:certificate/xxx"
aws_route53_collect_zone_id = "ZXXXXX"

aws_cloudfront_otm_domain = ["otm.example.com"]
aws_cloudfront_otm_acm_certificate_arn = "arn:aws:acm:us-east-1:xxx:certificate/xxx"
aws_route53_otm_zone_id = "ZXXXXX"

aws_cloudfront_client_domain = ["client.example,com"]
aws_cloudfront_client_acm_certificate_arn = "arn:aws:acm:us-east-1:xxx:certificate/xxx"
aws_route53_client_zone_id = "ZXXXXX"
```

Before that, you need create a s3 bucket for terraform backend.
And set bucket name to `TERRAFORM_BACKEND_BUCKET` environment variable.

```
docker build -t otm-setup .
docker run -e 'AWS_PROFILE=YOUR_PROFILE' \
           -e 'AWS_DEFAULT_REGION=YOUR_REGION' \
           -e 'TERRAFORM_BACKEND_BUCKET=YOUR_TERRAFORM_BACKEND_BUCKET' \
           -e 'ROOT_EMAIL=YOUR_ROOT_USER_EMAIL' \
           -v `pwd`:/otm  \
           -v $HOME/.aws:/root/.aws \
           -v /var/run/docker.sock:/var/run/docker.sock  \
           -it otm-setup:latest python deploy.py
```

## (2) for Development

### Web API: Local Run

```
cd client_apis
pip install chalice
export AWS_PROFILE=xxxx
chalice local
```

### Client: Local Run

```
cd client
yarn install
yarn run start
```

Open `http://localhost:8080`


## (3) Delete application

```
docker run -e 'AWS_PROFILE=YOUR_PROFILE' \
          -e 'AWS_DEFAULT_REGION=YOUR_REGION' \
          -v `pwd`:/otm  \
          -v $HOME/.aws:/root/.aws \
          -v /var/run/docker.sock:/var/run/docker.sock  \
          -it otm-setup:latest python delete.py
```

Dry-run

```
docker run -e 'AWS_PROFILE=YOUR_PROFILE' \
          -e 'AWS_DEFAULT_REGION=YOUR_REGION' \
          -v `pwd`:/otm  \
          -v $HOME/.aws:/root/.aws \
          -v /var/run/docker.sock:/var/run/docker.sock  \
          -it otm-setup:latest python delete.py --dry-run
```
