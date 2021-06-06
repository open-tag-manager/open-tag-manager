provider "aws" {}

terraform {
  backend "s3" {
  }
}


resource "aws_s3_bucket" "otm_collect" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-collect"
  acl = "public-read"

  cors_rule {
    allowed_headers = []
    allowed_methods = [
      "GET"]
    allowed_origins = [
      "*"]
    expose_headers = []
  }
  tags = var.aws_resource_tags
}

resource "aws_s3_bucket_object" "otm_collect" {
  bucket = aws_s3_bucket.otm_collect.id
  key = "collect.html"
  source = "../../collect.html"
  acl = "public-read"
  content_type = "text/html"
}

data "aws_canonical_user_id" "current" {}

resource "aws_s3_bucket" "otm_collect_log" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-collect-log"
  tags = var.aws_resource_tags

  grant {
    id          = data.aws_canonical_user_id.current.id
    type        = "CanonicalUser"
    permissions = ["FULL_CONTROL"]
  }

  grant {
    id          = "c4c1ede66af53448b93c283ce9448c4ba468c9432aa01d700d3878632f77d2d0"
    type        = "CanonicalUser"
    permissions = ["FULL_CONTROL"]
  }
}

locals {
  s3_collect_origin_id = "s3otmCollect"
  s3_script_origin_id = "s3otmScript"
  s3_client_origin_id = "s3otmClient"
}

resource "aws_cloudfront_distribution" "otm_collect_distribution" {
  origin {
    domain_name = aws_s3_bucket.otm_collect.bucket_regional_domain_name
    origin_id = local.s3_collect_origin_id
  }

  aliases = var.aws_cloudfront_collect_domain
  viewer_certificate {
    acm_certificate_arn = var.aws_cloudfront_collect_acm_certificate_arn
    cloudfront_default_certificate = var.aws_cloudfront_collect_acm_certificate_arn == "" ? true : false
    ssl_support_method = "sni-only"
  }

  enabled = true
  is_ipv6_enabled = true
  comment = "otm collect distribution"
  default_root_object = "collect.html"

  logging_config {
    include_cookies = false
    bucket = aws_s3_bucket.otm_collect_log.bucket_domain_name
    prefix = "cflog/"
  }

  default_cache_behavior {
    allowed_methods = [
      "GET",
      "HEAD"]
    cached_methods = [
      "GET",
      "HEAD"]
    target_origin_id = local.s3_collect_origin_id

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl = 0
    default_ttl = 3600
    max_ttl = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  custom_error_response {
    error_caching_min_ttl = 3600
    error_code = 403
    response_code = 200
    response_page_path = "/collect.html"
  }

  custom_error_response {
    error_caching_min_ttl = 3600
    error_code = 404
    response_code = 200
    response_page_path = "/collect.html"
  }

  tags = var.aws_resource_tags
}

resource "aws_sns_topic" "otm_collect_log_topic" {
  name = "${terraform.workspace}-otm-collect-log-topic"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "*"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:*:*:${terraform.workspace}-otm-collect-log-topic",
    "Condition": {
      "ArnLike": {"aws:SourceArn":"${aws_s3_bucket.otm_collect_log.arn}"}
    }
  }]
}
POLICY
}

resource "aws_s3_bucket_notification" "otm_collect_log_notification" {
  bucket = aws_s3_bucket.otm_collect_log.id

  topic {
    topic_arn = aws_sns_topic.otm_collect_log_topic.arn
    events = [
      "s3:ObjectCreated:*"]
    filter_prefix = "cflog/"
  }
}

resource "aws_s3_bucket" "otm_script" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-script"
  acl = "private"
  tags = var.aws_resource_tags
}

resource "aws_cloudfront_distribution" "otm_script_distribution" {
  origin {
    domain_name = aws_s3_bucket.otm_script.bucket_regional_domain_name
    origin_id = local.s3_script_origin_id
  }

  aliases = var.aws_cloudfront_otm_domain
  viewer_certificate {
    acm_certificate_arn = var.aws_cloudfront_otm_acm_certificate_arn
    cloudfront_default_certificate = var.aws_cloudfront_otm_acm_certificate_arn == "" ? true : false
    ssl_support_method = "sni-only"
  }

  enabled = true
  is_ipv6_enabled = true
  comment = "otm script distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods = [
      "GET",
      "HEAD"]
    cached_methods = [
      "GET",
      "HEAD"]
    target_origin_id = local.s3_script_origin_id

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl = 0
    default_ttl = 3600
    max_ttl = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = var.aws_resource_tags
}

resource "aws_s3_bucket" "otm_stats" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-stats"
  acl = "private"

  cors_rule {
    allowed_headers = []
    allowed_methods = [
      "GET"]
    allowed_origins = [
      "*"]
    expose_headers = []
  }
  tags = var.aws_resource_tags
}

resource "aws_s3_bucket" "otm_client" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-client"
  acl = "public-read"
  tags = var.aws_resource_tags
}

resource "aws_cloudfront_distribution" "otm_client_distribution" {
  origin {
    domain_name = aws_s3_bucket.otm_client.bucket_regional_domain_name
    origin_id = local.s3_client_origin_id
  }

  aliases = var.aws_cloudfront_client_domain
  viewer_certificate {
    acm_certificate_arn = var.aws_cloudfront_client_acm_certificate_arn
    cloudfront_default_certificate = var.aws_cloudfront_client_acm_certificate_arn == "" ? true : false
    ssl_support_method = "sni-only"
  }
  enabled = true
  is_ipv6_enabled = true
  comment = "otm client distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods = [
      "GET",
      "HEAD"]
    cached_methods = [
      "GET",
      "HEAD"]
    target_origin_id = local.s3_client_origin_id

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl = 0
    default_ttl = 3600
    max_ttl = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  custom_error_response {
    error_caching_min_ttl = 3600
    error_code = 403
    response_code = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_caching_min_ttl = 3600
    error_code = 404
    response_code = 200
    response_page_path = "/index.html"
  }

  tags = var.aws_resource_tags
}

resource "aws_s3_bucket" "otm_config" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-config"
  acl = "private"
  tags = var.aws_resource_tags
}

resource "aws_dynamodb_table" "otm_org" {
  name = "${terraform.workspace}_otm_org"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "name"

  attribute {
    name = "name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "otm_user" {
  name = "${terraform.workspace}_otm_user"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "username"

  attribute {
    name = "username"
    type = "S"
  }
}

resource "aws_dynamodb_table" "otm_role" {
  name = "${terraform.workspace}_otm_role"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "username"
  range_key = "organization"

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "organization"
    type = "S"
  }

  global_secondary_index {
    name               = "organization_index"
    hash_key           = "organization"
    projection_type    = "ALL"
  }
}

resource "aws_dynamodb_table" "otm_container" {
  name = "${terraform.workspace}_otm_container"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "tid"

  attribute {
    name = "tid"
    type = "S"
  }

  attribute {
    name = "organization"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name               = "organization_index"
    hash_key           = "organization"
    range_key          = "created_at"
    projection_type    = "ALL"
  }
}

resource "aws_dynamodb_table" "otm_stat" {
  name = "${terraform.workspace}_otm_stat"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "tid"
  range_key = "timestamp"

  attribute {
    name = "tid"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }
}

resource "aws_dynamodb_table" "otm_usage" {
  name = "${terraform.workspace}_otm_usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "organization"
  range_key = "month"

  attribute {
    name = "organization"
    type = "S"
  }

  attribute {
    name = "month"
    type = "N"
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${terraform.workspace}_otm_ecs_task_role"
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
    {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
        }
    }
    ]
}
EOF
}

resource "aws_iam_policy" "log_stat_s3_access_policy" {
  name = "${terraform.workspace}_otm_log_stat_s3_access_policy"
  description = "Open Tag Manager S3 Policy"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
        "Effect": "Allow",
        "Action": [
            "athena:*"
        ],
        "Resource": [
            "*"
        ]
    },
    {
        "Effect": "Allow",
        "Action": [
            "glue:CreateDatabase",
            "glue:DeleteDatabase",
            "glue:GetDatabase",
            "glue:GetDatabases",
            "glue:UpdateDatabase",
            "glue:CreateTable",
            "glue:DeleteTable",
            "glue:BatchDeleteTable",
            "glue:UpdateTable",
            "glue:GetTable",
            "glue:GetTables",
            "glue:BatchCreatePartition",
            "glue:CreatePartition",
            "glue:DeletePartition",
            "glue:BatchDeletePartition",
            "glue:UpdatePartition",
            "glue:GetPartition",
            "glue:GetPartitions",
            "glue:BatchGetPartition"
        ],
        "Resource": [
            "*"
        ]
    },
    {
      "Effect": "Allow",
      "Action": [
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:GetObjectTagging",
          "s3:GetObjectVersionTagging",
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:PutObjectTagging",
          "s3:PutObjectVersionTagging",
          "s3:ListBucket",
          "s3:ListBucketVersions",
          "s3:GetBucketLocation"
      ],
      "Resource": [
        "${aws_s3_bucket.otm_collect_log.arn}/*",
        "${aws_s3_bucket.otm_collect_log.arn}",
        "${aws_s3_bucket.otm_stats.arn}/*",
        "${aws_s3_bucket.otm_stats.arn}",
        "${aws_s3_bucket.otm_config.arn}/*",
        "${aws_s3_bucket.otm_config.arn}",
        "${aws_s3_bucket.otm_athena.arn}/*",
        "${aws_s3_bucket.otm_athena.arn}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "${aws_dynamodb_table.otm_org.arn}",
        "${aws_dynamodb_table.otm_stat.arn}",
        "${aws_dynamodb_table.otm_container.arn}",
        "${aws_dynamodb_table.otm_usage.arn}"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "esc_task_role" {
  role = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_s3" {
  role = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.log_stat_s3_access_policy.arn
}

resource "aws_ecr_repository" "otm_data_retriever" {
  name = "${terraform.workspace}_otm-data-retriever"
}

resource "aws_batch_job_definition" "otm_data_retriever" {
  name = "${terraform.workspace}_otm_data_retriever_job_definition"
  type = "container"
  timeout {
    attempt_duration_seconds = var.aws_batch_timeout
  }
  container_properties = <<CONTAINER_PROPERTIES
{
  "command": ["python", "app.py"],
  "image": "${aws_ecr_repository.otm_data_retriever.repository_url}:latest",
  "jobRoleArn": "${aws_iam_role.ecs_task_role.arn}",
  "memory": 2000,
  "vcpus": 2,
  "volumes": [],
  "environment": [
    {"name": "AWS_DEFAULT_REGION", "value": "${var.aws_region}"},
    {"name": "OTM_STATS_BUCKET", "value": "${aws_s3_bucket.otm_stats.bucket}"},
    {"name": "OTM_STATS_PREFIX", "value": "stats/"},
    {"name": "OTM_USAGE_PREFIX", "value": "usage/"},
    {"name": "STATS_ATHENA_RESULT_BUCKET", "value": "${aws_s3_bucket.otm_athena.bucket}"},
    {"name": "STATS_ATHENA_RESULT_PREFIX", "value": ""},
    {"name": "STATS_ATHENA_DATABASE", "value": "${aws_athena_database.otm.name}"},
    {"name": "STATS_ATHENA_TABLE", "value": "otm_collect"},
    {"name": "USAGE_ATHENA_TABLE", "value": "otm_usage"},
    {"name": "OTM_STAT_DYNAMODB_TABLE", "value": "${aws_dynamodb_table.otm_stat.name}"},
    {"name": "OTM_USAGE_DYNAMODB_TABLE", "value": "${aws_dynamodb_table.otm_usage.name}"},
    {"name": "OTM_CONTAINER_DYNAMODB_TABLE", "value": "${aws_dynamodb_table.otm_container.name}"}
  ],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_batch_job_definition" "otm_data_retriever_usage" {
  name = "${terraform.workspace}_otm_data_retriever_usage_job_definition"
  type = "container"
  timeout {
    attempt_duration_seconds = var.aws_batch_timeout
  }
  container_properties = <<CONTAINER_PROPERTIES
{
  "command": ["python", "usage.py"],
  "image": "${aws_ecr_repository.otm_data_retriever.repository_url}:latest",
  "jobRoleArn": "${aws_iam_role.ecs_task_role.arn}",
  "memory": 2000,
  "vcpus": 2,
  "volumes": [],
  "environment": [
    {"name": "AWS_DEFAULT_REGION", "value": "${var.aws_region}"},
    {"name": "STATS_ATHENA_RESULT_BUCKET", "value": "${aws_s3_bucket.otm_athena.bucket}"},
    {"name": "STATS_ATHENA_RESULT_PREFIX", "value": ""},
    {"name": "STATS_ATHENA_DATABASE", "value": "${aws_athena_database.otm.name}"},
    {"name": "USAGE_ATHENA_TABLE", "value": "otm_usage"},
    {"name": "OTM_USAGE_DYNAMODB_TABLE", "value": "${aws_dynamodb_table.otm_usage.name}"}
  ],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_iam_role" "data_retriever_usage_role" {
  name = "${terraform.workspace}_otm_data_retriever_usage_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "data_retriever_usage_policy" {
  name = "${terraform.workspace}_otm_data_retriever_usage_policy"
  description = "Open Tag Manager, CloudWatch target role"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
       {
          "Effect": "Allow",
          "Action": [
               "batch:SubmitJob"
           ],
           "Resource": "*"
        }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "data_retriever_usage_policy_attachment" {
  role = aws_iam_role.data_retriever_usage_role.name
  policy_arn = aws_iam_policy.data_retriever_usage_policy.arn
}

resource "aws_cloudwatch_event_rule" "otm_usage_report" {
  name                = "${terraform.workspace}_otm_usage_report"
  description         = "[OTM] usage report"
  schedule_expression = "cron(20 0 1 * ? *)"
  is_enabled          = var.aws_cloudwatch_event_usage_enable
}

resource "aws_cloudwatch_event_target" "otm_data_retriever_usage" {
  rule         = aws_cloudwatch_event_rule.otm_usage_report.name
  target_id    = "${terraform.workspace}_otm_data_retriever_usage"
  arn          = var.aws_batch_job_queue_arn
  role_arn     = aws_iam_role.data_retriever_usage_role.arn
  batch_target {
    job_definition = aws_batch_job_definition.otm_data_retriever_usage.arn
    job_name       = "${terraform.workspace}_otm_data_retriever_usage"
  }
}

resource "aws_s3_bucket" "otm_athena" {
  bucket = "${terraform.workspace}-${var.aws_s3_bucket_prefix}-otm-athena"
  acl = "private"
  tags = var.aws_resource_tags
}

resource "aws_athena_database" "otm" {
  name = "${terraform.workspace}_otm"
  bucket = aws_s3_bucket.otm_athena.bucket
}

resource "aws_route53_record" "collect" {
  count = length(var.aws_cloudfront_collect_domain) > 0 ? 1 : 0
  zone_id = var.aws_route53_collect_zone_id
  name = var.aws_cloudfront_collect_domain[0]
  type = "A"

  alias {
    name = aws_cloudfront_distribution.otm_collect_distribution.domain_name
    zone_id = aws_cloudfront_distribution.otm_collect_distribution.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "otm" {
  count = length(var.aws_cloudfront_otm_domain) > 0 ? 1 : 0
  zone_id = var.aws_route53_otm_zone_id
  name = var.aws_cloudfront_otm_domain[0]
  type = "A"

  alias {
    name = aws_cloudfront_distribution.otm_script_distribution.domain_name
    zone_id = aws_cloudfront_distribution.otm_script_distribution.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "client" {
  count = length(var.aws_cloudfront_client_domain) > 0 ? 1 : 0
  zone_id = var.aws_route53_client_zone_id
  name = var.aws_cloudfront_client_domain[0]
  type = "A"

  alias {
    name = aws_cloudfront_distribution.otm_client_distribution.domain_name
    zone_id = aws_cloudfront_distribution.otm_client_distribution.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_cognito_user_pool" "otm" {
  name = "${terraform.workspace}_otm_user"
  auto_verified_attributes = ["email"]
  alias_attributes = ["email"]
  schema {
    attribute_data_type = "String"
    name = "email"
    required = true
  }
  username_configuration {
    case_sensitive = false
  }
  tags = var.aws_resource_tags
  lifecycle {
    ignore_changes = [schema]
  }
}

resource "aws_cognito_user_pool_client" "otm" {
  name = "${terraform.workspace}_otm_web_client"
  user_pool_id = aws_cognito_user_pool.otm.id
  generate_secret = false
}

resource "aws_cognito_identity_pool" "otm" {
  identity_pool_name = "${terraform.workspace}_otm_id"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id = aws_cognito_user_pool_client.otm.id
    provider_name = aws_cognito_user_pool.otm.endpoint
    server_side_token_check = false
  }
  tags = var.aws_resource_tags
}
