provider "aws" {
  region = "${var.aws_region}"
  profile = "${var.aws_profile}"
}

resource "aws_s3_bucket" "otm_collect" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-collect"
  acl = "public-read"

  cors_rule = {
    allowed_headers = []
    allowed_methods = [
      "GET"]
    allowed_origins = [
      "*"]
    expose_headers = []
  }
  tags = "${var.aws_resource_tags}"
}

resource "aws_s3_bucket_object" "otm_collect" {
  bucket = "${aws_s3_bucket.otm_collect.id}"
  key = "collect.html"
  source = "../../collect.html"
  acl = "public-read"
  content_type = "text/html"
}

resource "aws_s3_bucket" "otm_collect_log" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-collect-log"
  acl = "private"
  tags = "${var.aws_resource_tags}"
}

locals {
  s3_collect_origin_id = "s3otmCollect"
  s3_script_origin_id = "s3otmScript"
  s3_client_origin_id = "s3otmClient"
}

resource "aws_cloudfront_distribution" "otm_collect_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_collect.bucket_regional_domain_name}"
    origin_id = "${local.s3_collect_origin_id}"
  }

  aliases = "${var.aws_cloudfront_collect_domain}"
  viewer_certificate = {
    acm_certificate_arn = "${var.aws_cloudfront_collect_acm_certificate_arn}"
    cloudfront_default_certificate = "${var.aws_cloudfront_collect_acm_certificate_arn == "" ? true : false}"
    ssl_support_method = "sni-only"
  }

  enabled = true
  is_ipv6_enabled = true
  comment = "otm collect distribution"
  default_root_object = "collect.html"

  logging_config {
    include_cookies = false
    bucket = "${aws_s3_bucket.otm_collect_log.bucket_domain_name}"
    prefix = "cflog/"
  }

  default_cache_behavior {
    allowed_methods = [
      "GET",
      "HEAD"]
    cached_methods = [
      "GET",
      "HEAD"]
    target_origin_id = "${local.s3_collect_origin_id}"

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

  tags = "${var.aws_resource_tags}"
}

resource "aws_sns_topic" "otm_collect_log_topic" {
  name = "${terraform.env}-otm-collect-log-topic"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "*"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:*:*:${terraform.env}-otm-collect-log-topic",
    "Condition": {
      "ArnLike": {"aws:SourceArn":"${aws_s3_bucket.otm_collect_log.arn}"}
    }
  }]
}
POLICY
}

resource "aws_s3_bucket_notification" "otm_collect_log_notification" {
  bucket = "${aws_s3_bucket.otm_collect_log.id}"

  topic = {
    topic_arn = "${aws_sns_topic.otm_collect_log_topic.arn}"
    events = [
      "s3:ObjectCreated:*"],
    filter_prefix = "cflog/"
  }
}

resource "aws_s3_bucket" "otm_script" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-script"
  acl = "private"
  tags = "${var.aws_resource_tags}"
}

resource "aws_cloudfront_distribution" "otm_script_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_script.bucket_regional_domain_name}"
    origin_id = "${local.s3_script_origin_id}"
  }

  aliases = "${var.aws_cloudfront_otm_domain}"
  viewer_certificate = {
    acm_certificate_arn = "${var.aws_cloudfront_otm_acm_certificate_arn}"
    cloudfront_default_certificate = "${var.aws_cloudfront_otm_acm_certificate_arn == "" ? true : false}"
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
    target_origin_id = "${local.s3_script_origin_id}"

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

  tags = "${var.aws_resource_tags}"
}

resource "aws_s3_bucket" "otm_stats" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-stats"
  acl = "private"

  cors_rule = {
    allowed_headers = []
    allowed_methods = [
      "GET"]
    allowed_origins = [
      "*"]
    expose_headers = []
  }
  tags = "${var.aws_resource_tags}"
}

resource "aws_s3_bucket" "otm_client" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-client"
  acl = "public-read"
  tags = "${var.aws_resource_tags}"
}

resource "aws_cloudfront_distribution" "otm_client_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_client.bucket_regional_domain_name}"
    origin_id = "${local.s3_client_origin_id}"
  }

  aliases = "${var.aws_cloudfront_client_domain}"
  viewer_certificate = {
    acm_certificate_arn = "${var.aws_cloudfront_client_acm_certificate_arn}"
    cloudfront_default_certificate = "${var.aws_cloudfront_client_acm_certificate_arn == "" ? true : false}"
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
    target_origin_id = "${local.s3_client_origin_id}"

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

  tags = "${var.aws_resource_tags}"
}

resource "aws_s3_bucket" "otm_config" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-config"
  acl = "private"
  tags = "${var.aws_resource_tags}"
}

resource "aws_dynamodb_table" "otm_role" {
  name = "${terraform.env}_otm_role"
  read_capacity = 1
  write_capacity = 1
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
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${terraform.env}_otm_ecs_task_role"
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
  name = "${terraform.env}_otm_log_stat_s3_access_policy"
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
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "esc_task_role" {
  role = "${aws_iam_role.ecs_task_role.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_s3" {
  role = "${aws_iam_role.ecs_task_role.name}"
  policy_arn = "${aws_iam_policy.log_stat_s3_access_policy.arn}"
}

resource "aws_ecr_repository" "otm_data_retriever" {
  name = "${terraform.env}_otm-data-retriever"
}

resource "aws_batch_job_definition" "otm_data_retriever" {
  name = "${terraform.env}_otm_data_retriever_job_definition"
  type = "container"
  timeout = {
    attempt_duration_seconds = "${var.aws_batch_timeout}"
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
    {"name": "AWS_DEFAULT_REGION", "value": "${var.aws_region}"}
  ],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_s3_bucket" "otm_athena" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-athena"
  acl = "private"
  tags = "${var.aws_resource_tags}"
}

resource "aws_athena_database" "otm" {
  name = "${terraform.env}_${terraform.env}_otm_a2bq"
  bucket = "${aws_s3_bucket.otm_athena.bucket}"
}

resource "aws_route53_record" "collect" {
  count = "${length(var.aws_cloudfront_collect_domain) > 0 ? 1 : 0}"
  zone_id = "${var.aws_route53_collect_zone_id}"
  name = "${var.aws_cloudfront_collect_domain[0]}"
  type = "A"

  alias = {
    name = "${aws_cloudfront_distribution.otm_collect_distribution.domain_name}"
    zone_id = "${aws_cloudfront_distribution.otm_collect_distribution.hosted_zone_id}"
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "otm" {
  count = "${length(var.aws_cloudfront_otm_domain) > 0 ? 1 : 0}"
  zone_id = "${var.aws_route53_otm_zone_id}"
  name = "${var.aws_cloudfront_otm_domain[0]}"
  type = "A"

  alias = {
    name = "${aws_cloudfront_distribution.otm_script_distribution.domain_name}"
    zone_id = "${aws_cloudfront_distribution.otm_script_distribution.hosted_zone_id}"
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "client" {
  count = "${length(var.aws_cloudfront_client_domain) > 0 ? 1 : 0}"
  zone_id = "${var.aws_route53_client_zone_id}"
  name = "${var.aws_cloudfront_client_domain[0]}"
  type = "A"

  alias = {
    name = "${aws_cloudfront_distribution.otm_client_distribution.domain_name}"
    zone_id = "${aws_cloudfront_distribution.otm_client_distribution.hosted_zone_id}"
    evaluate_target_health = false
  }
}

resource "aws_cognito_identity_pool" "otm" {
  identity_pool_name = "${terraform.env}_otm_id"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id = "${var.aws_cognito_user_pool_client_id}"
    provider_name = "cognito-idp.${var.aws_region}.amazonaws.com/${var.aws_cognito_user_pool_id}"
    server_side_token_check = false
  }
}
