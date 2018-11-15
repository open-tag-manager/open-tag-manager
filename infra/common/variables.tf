variable "aws_access_key" {}
variable "aws_secret_key" {}
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
variable "aws_route53_zone_id" {
  type = "string"
  default = ""
}
variable "google_project_id" {}
variable "google_region" {}

variable "aws_s3_bucket_prefix" {}

variable "google_bigquery_dataset_location" {}
variable "google_storage_location" {}

