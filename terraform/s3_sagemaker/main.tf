terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "mlops_bucket" {
  bucket = var.bucket_name
  acl    = "private"
}

resource "aws_sns_topic" "alerts" {
  name = "mlops-alerts"
}

resource "aws_iam_role" "sagemaker_role" {
  name = "mlops-sagemaker-role"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_assume_role_policy.json
}

data "aws_iam_policy_document" "sagemaker_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "sagemaker_role_policy" {
  name = "mlops-sagemaker-role-policy"
  role = aws_iam_role.sagemaker_role.id
  policy = file("${path.module}/../../docs/iam/sagemaker_role_policy.json")
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "bucket_name" {
  type = string
}
