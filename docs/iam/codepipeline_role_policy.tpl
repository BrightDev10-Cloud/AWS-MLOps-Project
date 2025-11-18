{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3Artifacts",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "${artifacts_bucket_arn}",
        "${artifacts_bucket_arn}/*"
      ]
    },
    {
      "Sid": "AllowCodeBuild",
      "Effect": "Allow",
      "Action": [
        "codebuild:StartBuild",
        "codebuild:BatchGetBuilds",
        "codebuild:BatchGetProjects"
      ],
      "Resource": "${codebuild_project_arn}"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
