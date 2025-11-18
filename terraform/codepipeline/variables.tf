variable "region" {
  type    = string
  default = "us-east-1"
}

variable "artifacts_bucket_name" {
  type = string
}

variable "s3_bucket" {
  type = string
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "branch" {
  type    = string
  default = "main"
}

variable "codestar_connection_arn" {
  type = string
  description = "ARN of an existing AWS CodeStar Connections connection to GitHub. Create in console or via resource aws_codestarconnections_connection."
}

variable "ecr_repo_arn" {
  type    = string
  default = ""
  description = "Optional: ARN of the ECR repository to allow pushes from CodeBuild. If empty, update template accordingly."
}

variable "sagemaker_model_arn" {
  type    = string
  default = ""
  description = "Optional: ARN of an existing SageMaker model to scope SageMaker permissions."
}

variable "sagemaker_endpoint_arn" {
  type    = string
  default = ""
  description = "Optional: ARN of an existing SageMaker endpoint to scope SageMaker permissions."
}

variable "sagemaker_role_arn" {
  type    = string
  default = ""
  description = "Optional: ARN of the SageMaker execution role that CodeBuild should be allowed to pass."
}
