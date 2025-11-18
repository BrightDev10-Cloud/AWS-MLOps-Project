Deprecated IAM policy files

The legacy JSON policy files `codebuild_role_policy.json` and `codepipeline_role_policy.json` have been replaced by templated policy files (`*.tpl`) which Terraform renders with the correct ARNs (artifact bucket, ECR repo, SageMaker ARNs).

If you want to remove the old JSON files from the repository manually, run:

```bash
# from repo root
rm docs/iam/codebuild_role_policy.json
rm docs/iam/codepipeline_role_policy.json
git add -A
git commit -m "Remove deprecated IAM JSON policy files; using templated policies"
git push
```

Note: I attempted to update/remove the second JSON file programmatically but encountered a tool error; please remove it manually if desired. The repository now uses `codebuild_role_policy.tpl` and `codepipeline_role_policy.tpl` and the Terraform module renders them with `templatefile(... )`.
