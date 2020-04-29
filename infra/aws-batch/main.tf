provider "aws" {
  profile = var.aws_profile
  region = var.aws_region
}

terraform {
  backend "s3" {
  }
}


resource "aws_iam_role" "ecs_instance_role" {
  name = "${terraform.workspace}_otm_ecs_instance_role"
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
    {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
        "Service": "ec2.amazonaws.com"
        }
    }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = "${terraform.workspace}_otm_ecs_instance_role"
  role = aws_iam_role.ecs_instance_role.name
}

resource "aws_iam_role" "aws_batch_service_role" {
  name = "${terraform.workspace}_otm_aws_batch_service_role"
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
    {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
        "Service": "batch.amazonaws.com"
        }
    }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
  role = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

resource "aws_security_group" "batch" {
  name = "${terraform.workspace}_otm_batch_compute_environment_security_group"
  vpc_id = aws_vpc.otm.id
  ingress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    self = true
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = [
      "0.0.0.0/0"]
  }

  tags = var.aws_resource_tags
}

resource "aws_vpc" "otm" {
  cidr_block = "10.1.0.0/16"
  tags = var.aws_resource_tags
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.otm.id

  tags = var.aws_resource_tags
}

resource "aws_route_table" "r" {
  vpc_id = aws_vpc.otm.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = var.aws_resource_tags
}

resource "aws_subnet" "otm" {
  vpc_id = aws_vpc.otm.id
  cidr_block = "10.1.1.0/24"
  map_public_ip_on_launch = true
  tags = var.aws_resource_tags
}

resource "aws_route_table_association" "route_table_a" {
  subnet_id = aws_subnet.otm.id
  route_table_id = aws_route_table.r.id
}

resource "aws_batch_compute_environment" "compute_environment" {
  compute_environment_name = "${terraform.workspace}_otm-compute-env"
  compute_resources {
    instance_role = aws_iam_instance_profile.ecs_instance_role.arn
    instance_type = [
      "optimal",
    ]
    max_vcpus = 2
    min_vcpus = 0
    security_group_ids = [
      aws_security_group.batch.id
    ]
    subnets = [
      aws_subnet.otm.id
    ]
    type = "EC2"
    tags = var.aws_resource_tags
  }
  service_role = aws_iam_role.aws_batch_service_role.arn
  type = "MANAGED"
  depends_on = [
    aws_iam_role_policy_attachment.aws_batch_service_role
  ]
}

resource "aws_batch_job_queue" "otm" {
  name = "${terraform.workspace}_otm"
  state = "ENABLED"
  priority = 1
  compute_environments = [
    aws_batch_compute_environment.compute_environment.arn
  ]
}
