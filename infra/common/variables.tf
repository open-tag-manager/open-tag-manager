variable "aws_profile" {}
variable "aws_region" {}
variable "aws_batch_timeout" {
  default = 1800
}
variable "aws_batch_job_queue_arn" {}
variable "aws_cloudwatch_schedule_enabled" {
  default = false
}
variable "aws_cloudfront_collect_domain" {
  type = "list"
  default = []
}
variable "aws_cloudfront_collect_acm_certificate_arn" {
  type = "string"
  default = ""
}
variable "aws_cloudfront_otm_domain" {
  type = "list"
  default = []
}
variable "aws_cloudfront_otm_acm_certificate_arn" {
  type = "string"
  default = ""
}
variable "aws_cloudfront_client_domain" {
  type = "list"
  default = []
}
variable "aws_cloudfront_client_acm_certificate_arn" {
  type = "string"
  default = ""
}
variable "aws_route53_collect_zone_id" {
  type = "string"
  default = ""
}
variable "aws_route53_otm_zone_id" {
  type = "string"
  default = ""
}
variable "aws_route53_client_zone_id" {
  type = "string"
  default = ""
}
variable "aws_cognito_user_pool_id" {
  type = "string"
}
variable "aws_cognito_user_pool_client_id" {
  type = "string"
}

variable "aws_s3_bucket_prefix" {}
variable "aws_resource_tags" {
  type = "map"
  default = {
  }
}
