provider "aws" {
  access_key = "${var.aws_access_key}"
  secret_key = "${var.aws_secret_key}"
  region     = "${var.aws_region}"
}

provider "google" {
  credentials = "${file("account.json")}"
  project     = "${var.google_project_id}"
  region      = "${var.google_region}"
}

resource "aws_s3_bucket" "otm_collect" {
  bucket = "${var.aws_s3_bucket_prefix}-otm-collect"
  acl    = "public-read"

  cors_rule = {
    allowed_headers = []
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    expose_headers  = []
  }
}

resource "aws_s3_bucket_object" "otm_collect" {
  bucket = "${aws_s3_bucket.otm_collect.id}"
  key    = "collect.html"
  source = "collect.html"
  acl    = "public-read"
  content_type = "text/html"
}

resource "aws_s3_bucket" "otm_collect_log" {
  bucket = "${var.aws_s3_bucket_prefix}-otm-collect-log"
  acl    = "private"
}

locals {
  s3_collect_origin_id = "s3otmCollect"
  s3_script_origin_id  = "s3otmScript"
  s3_client_origin_id  = "s3otmClient"
}

resource "aws_cloudfront_distribution" "otm_collect_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_collect.bucket_regional_domain_name}"
    origin_id   = "${local.s3_collect_origin_id}"
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "otm collect distribution"
  default_root_object = "collect.html"

  logging_config {
    include_cookies = false
    bucket          = "${aws_s3_bucket.otm_collect_log.bucket_domain_name}"
    prefix          = "cflog/"
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${local.s3_collect_origin_id}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
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

resource "aws_s3_bucket" "otm_script" {
  bucket = "${var.aws_s3_bucket_prefix}-otm-script"
  acl    = "private"
}

resource "aws_s3_bucket_object" "otm_otm" {
  bucket = "${aws_s3_bucket.otm_script.id}"
  key    = "otm.js"
  source = "dist/otm.js"
  acl    = "public-read"
  content_type = "text/javascript"
}

resource "aws_cloudfront_distribution" "otm_script_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_script.bucket_regional_domain_name}"
    origin_id   = "${local.s3_script_origin_id}"
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "otm script distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${local.s3_script_origin_id}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
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
  bucket = "${var.aws_s3_bucket_prefix}-otm-stats"
  acl    = "private"
}

resource "aws_s3_bucket" "otm_client" {
  bucket = "${var.aws_s3_bucket_prefix}-otm-client"
  acl    = "public-read"
}

resource "aws_cloudfront_distribution" "otm_client_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.otm_client.bucket_regional_domain_name}"
    origin_id   = "${local.s3_client_origin_id}"
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "otm client distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${local.s3_client_origin_id}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
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

resource "aws_dynamodb_table" "otm_session" {
  name           = "otm_session"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id    = "open_tag_manager"
  friendly_name = "open_tag_manager"
  description   = "open tag manager dataset"
  location      = "${var.google_bigquery_dataset_location}"
}
