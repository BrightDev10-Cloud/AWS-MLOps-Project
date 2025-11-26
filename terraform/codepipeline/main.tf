terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifacts_bucket_name
}

resource "aws_s3_bucket_acl" "artifacts_acl" {
  bucket = aws_s3_bucket.artifacts.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts_block" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "codebuild_role" {
  name = "mlops-codebuild-role"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume_role_policy.json
}

data "aws_iam_policy_document" "codebuild_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "codebuild_policy" {
  name   = "mlops-codebuild-policy"
  role   = aws_iam_role.codebuild_role.id
  policy = templatefile("${path.module}/../../docs/iam/codebuild_role_policy.tpl", {
    artifacts_bucket_arn    = aws_s3_bucket.artifacts.arn,
    ecr_repo_arn            = var.ecr_repo_arn,
    sagemaker_model_arn    = var.sagemaker_model_arn,
    sagemaker_endpoint_arn = var.sagemaker_endpoint_arn,
    sagemaker_role_arn     = var.sagemaker_role_arn
  })
}

resource "aws_codebuild_project" "project" {
  name          = "mlops-codebuild"
  service_role  = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "S3"
    location = aws_s3_bucket.artifacts.bucket
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:6.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = false
    environment_variable {
      name  = "S3_BUCKET"
      value = var.s3_bucket
    }
  }

  source {
    type      = "GITHUB"
    location  = "${var.github_owner}/${var.github_repo}"
    buildspec = file("${path.root}/buildspec.yml")
  }
}

resource "aws_iam_role" "codepipeline_role" {
  name = "mlops-codepipeline-role"
  assume_role_policy = data.aws_iam_policy_document.codepipeline_assume_role_policy.json
}

data "aws_iam_policy_document" "codepipeline_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name   = "mlops-codepipeline-policy"
  role   = aws_iam_role.codepipeline_role.id
  policy = templatefile("${path.module}/../../docs/iam/codepipeline_role_policy.tpl", {
    artifacts_bucket_arn  = aws_s3_bucket.artifacts.arn,
    codebuild_project_arn = aws_codebuild_project.project.arn
  })
}

resource "aws_codepipeline" "pipeline" {
  name     = "mlops-pipeline"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    type = "S3"
    location = aws_s3_bucket.artifacts.bucket
  }

  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]
      configuration = {
        ConnectionArn = var.codestar_connection_arn
        FullRepositoryId = "${var.github_owner}/${var.github_repo}"
        BranchName = var.branch
      }
    }
  }

  stage {
    name = "Build"
    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      configuration = {
        ProjectName = aws_codebuild_project.project.name
      }
      version = "1"
    }
  }
}
