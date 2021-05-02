variable "aws_region" {}
variable "aws_batch_timeout" {
  default = 1800
}
variable "aws_batch_job_queue_arn" {}
variable "aws_cloudfront_collect_domain" {
  type = list(string)
  default = []
}
variable "aws_cloudfront_collect_acm_certificate_arn" {
  type = string
  default = ""
}
variable "aws_cloudfront_otm_domain" {
  type = list(string)
  default = []
}
variable "aws_cloudfront_otm_acm_certificate_arn" {
  type = string
  default = ""
}
variable "aws_cloudfront_client_domain" {
  type = list(string)
  default = []
}
variable "aws_cloudfront_client_acm_certificate_arn" {
  type = string
  default = ""
}
variable "aws_route53_collect_zone_id" {
  type = string
  default = ""
}
variable "aws_route53_otm_zone_id" {
  type = string
  default = ""
}
variable "aws_route53_client_zone_id" {
  type = string
  default = ""
}
variable "aws_cognito_user_pool_id" {
  type = string
}
variable "aws_cognito_user_pool_client_id" {
  type = string
}

variable "aws_s3_bucket_prefix" {}
variable "aws_resource_tags" {
  type = map(string)
  default = {
  }
}
variable "aws_cloudwatch_event_usage_enable" {
  type = bool
  default = true
}

variable "aws_cloudwatch_event_goal_enable" {
  type = bool
  default = false
}
