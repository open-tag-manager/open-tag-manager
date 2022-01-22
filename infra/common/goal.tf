resource "aws_batch_job_definition" "otm_data_retriever_goal" {
  name = "${terraform.workspace}_otm_data_retriever_goal_job_definition"
  type = "container"
  timeout {
    attempt_duration_seconds = var.aws_batch_timeout
  }
  container_properties = <<CONTAINER_PROPERTIES
{
  "command": ["python", "goal.py"],
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
    {"name": "STATS_ATHENA_DATABASE", "value": "${aws_glue_catalog_database.otm.name}"},
    {"name": "STATS_ATHENA_TABLE", "value": "otm_collect"},
    {"name": "OTM_CONTAINER_DYNAMODB_TABLE", "value": "${aws_dynamodb_table.otm_container.name}"}
  ],
  "mountPoints": [],
  "ulimits": []
}
CONTAINER_PROPERTIES
}

resource "aws_iam_role" "data_retriever_goal_role" {
  name = "${terraform.workspace}_otm_data_retriever_goal_role"
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

resource "aws_iam_policy" "data_retriever_goal_policy" {
  name = "${terraform.workspace}_otm_data_retriever_goal_policy"
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

resource "aws_iam_role_policy_attachment" "data_retriever_goal_policy_attachment" {
  role = aws_iam_role.data_retriever_goal_role.name
  policy_arn = aws_iam_policy.data_retriever_goal_policy.arn
}

resource "aws_cloudwatch_event_rule" "otm_data_retriever_goal" {
  name                = "${terraform.workspace}_otm_data_retriever_goal"
  description         = "[OTM] retrieve goal result"
  schedule_expression = "cron(10 0 * * ? *)"
  is_enabled          = var.aws_cloudwatch_event_goal_enable
}

resource "aws_cloudwatch_event_target" "otm_data_retriever_goal" {
  rule         = aws_cloudwatch_event_rule.otm_data_retriever_goal.name
  target_id    = "${terraform.workspace}_otm_data_retriever_goal"
  arn          = var.aws_batch_job_queue_arn
  role_arn     = aws_iam_role.data_retriever_goal_role.arn
  batch_target {
    job_definition = aws_batch_job_definition.otm_data_retriever_goal.arn
    job_name       = "${terraform.workspace}_otm_data_retriever_goal"
  }
}
