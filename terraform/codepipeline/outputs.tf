output "pipeline_name" {
  value = aws_codepipeline.pipeline.name
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "codebuild_project" {
  value = aws_codebuild_project.project.name
}
