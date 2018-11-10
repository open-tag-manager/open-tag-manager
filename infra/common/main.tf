provider "aws" {
  access_key = "${var.aws_access_key}"
  secret_key = "${var.aws_secret_key}"
  region = "${var.aws_region}"
}

provider "google" {
  credentials = "${file("../../account.json")}"
  project = "${var.google_project_id}"
  region = "${var.google_region}"
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

  viewer_certificate {
    cloudfront_default_certificate = true
  }
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
}

resource "aws_s3_bucket_object" "otm_otm" {
  bucket = "${aws_s3_bucket.otm_script.id}"
  key = "otm.js"
  source = "../../dist/otm.js"
  acl = "public-read"
  content_type = "text/javascript"
}

resource "aws_cloudfront_distribution" "otm_script_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_script.bucket_regional_domain_name}"
    origin_id = "${local.s3_script_origin_id}"
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

  viewer_certificate {
    cloudfront_default_certificate = true
  }
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
}

resource "aws_s3_bucket" "otm_client" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-client"
  acl = "public-read"
}

resource "aws_cloudfront_distribution" "otm_client_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_client.bucket_regional_domain_name}"
    origin_id = "${local.s3_client_origin_id}"
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

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_s3_bucket" "otm_config" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-config"
  acl = "private"
}

resource "aws_s3_bucket_object" "gc_key" {
  bucket = "${aws_s3_bucket.otm_config.id}"
  key = "account.json"
  source = "../../account.json"
  acl = "private"
  server_side_encryption = "AES256"
}

resource "aws_dynamodb_table" "otm_session" {
  name = "${terraform.env}_otm_session"
  read_capacity = 1
  write_capacity = 1
  hash_key = "session_id"

  attribute {
    name = "session_id"
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

resource "aws_ecr_repository" "otm_athena2bigquery" {
  name = "${terraform.env}_otm-athena2bigquery"
}

resource "aws_batch_job_definition" "otm_data_retriever" {
  name = "${terraform.env}_otm_data_retriever_job_definition"
  type = "container"
  timeout = {
    attempt_duration_seconds = "${var.aws_batch_timeout}"
  }
  container_properties = <<CONTAINER_PROPERTIES
{
  "command": [],
  "image": "${aws_ecr_repository.otm_data_retriever.repository_url}:latest",
  "jobRoleArn": "${aws_iam_role.ecs_task_role.arn}",
  "memory": 2000,
  "vcpus": 2,
  "volumes": [],
  "environment": [],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_batch_job_definition" "otm_athena2bigquery" {
  name = "${terraform.env}_otm_athena2bigquery_job_definition"
  type = "container"
  timeout = {
    attempt_duration_seconds = "${var.aws_batch_timeout}"
  }
  container_properties = <<CONTAINER_PROPERTIES
{
  "command": [],
  "image": "${aws_ecr_repository.otm_athena2bigquery.repository_url}:latest",
  "jobRoleArn": "${aws_iam_role.ecs_task_role.arn}",
  "memory": 2000,
  "vcpus": 2,
  "volumes": [],
  "environment": [
    {"name": "CONFIG_BUCKET", "value": "${aws_s3_bucket.otm_config.id}"},
    {"name": "CONFIG_KEY", "value": "athena2bigquery-config.yml"},
    {"name": "GCLOUD_KEY", "value": "${aws_s3_bucket_object.gc_key.key}"}
  ],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_iam_role" "scheduled_batch" {
  name = "${terraform.env}_otm-scheduled-batch"
  assume_role_policy = <<DOC
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
DOC
}

resource "aws_iam_role_policy" "scheduled_batch" {
  name = "${terraform.env}_otm-scheduled-batch-policy"
  role = "${aws_iam_role.scheduled_batch.id}"
  policy = <<DOC
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
DOC
}

resource "aws_cloudwatch_event_rule" "athena2bigquery" {
  name = "${terraform.env}_ExecuteAthena2BigQuery"
  description = "Execute Athen2BigQuery"
  schedule_expression = "cron(0 2 * * ? *)"
  is_enabled = "${var.aws_cloudwatch_schedule_enabled}"
}

resource "aws_cloudwatch_event_target" "athena2bigquery" {
  rule = "${aws_cloudwatch_event_rule.athena2bigquery.name}"
  arn = "${var.aws_batch_job_queue_arn}"
  role_arn = "${aws_iam_role.scheduled_batch.arn}"
  batch_target = {
    job_definition = "${aws_batch_job_definition.otm_athena2bigquery.arn}"
    job_name = "athena2bigquery-daily"
  }
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id = "${terraform.env}_open_tag_manager"
  friendly_name = "${terraform.env}_open_tag_manager"
  description = "open tag manager dataset"
  location = "${var.google_bigquery_dataset_location}"
}

resource "google_storage_bucket" "bucket" {
  name = "${terraform.env}-${var.aws_s3_bucket_prefix}-open-tag-manager"
  location = "${var.google_storage_location}"
}

resource "aws_s3_bucket" "otm_athena" {
  bucket = "${terraform.env}-${var.aws_s3_bucket_prefix}-otm-athena"
  acl = "private"
}

resource "aws_athena_database" "otm" {
  name = "${terraform.env}_${terraform.env}_otm_a2bq"
  bucket = "${aws_s3_bucket.otm_athena.bucket}"
}
