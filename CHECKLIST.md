# 🚀 Getting Started Checklist

Use this checklist to set up your MLOps pipeline step by step.

## ☑️ Phase 1: Initial Setup

### Environment Preparation
- [ ] Clone the repository to your local machine
- [ ] Ensure Python 3.10+ is installed (`python --version`)
- [ ] Create virtual environment: `python3 -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`

### Configuration
- [ ] Copy environment template: `cp .env.example .env`
- [ ] Open `.env` in your editor
- [ ] Set `AWS_REGION` to your preferred region
- [ ] Set `AWS_ACCOUNT_ID` to your AWS account ID
- [ ] Create S3 bucket in AWS Console (or use existing)
- [ ] Set `S3_BUCKET` in `.env`
- [ ] Create SageMaker execution role in IAM
- [ ] Set `SAGEMAKER_ROLE_ARN` in `.env`
- [ ] Create ECR repository for serving container
- [ ] Set `ECR_IMAGE` in `.env`

### Verification
- [ ] Run tests to verify setup: `pytest -v`
- [ ] Check that all tests pass
- [ ] Review test output for any warnings

## ☑️ Phase 2: Data Pipeline

### Data Acquisition
- [ ] Download Telco Customer Churn dataset from Kaggle
- [ ] Place CSV file in project root or note its path
- [ ] Verify CSV is readable: `head -n 5 WA_Fn-UseC_-Telco-Customer-Churn.csv`

### Preprocessing
- [ ] Run preprocessing locally:
  ```bash
  python preprocess_telco.py \
    --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
    --output-dir processed
  ```
- [ ] Verify `processed/train.csv` was created
- [ ] Verify `processed/val.csv` was created
- [ ] Check data shapes are correct
- [ ] (Optional) Upload to S3:
  ```bash
  python preprocess_telco.py \
    --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
    --upload --s3-bucket $S3_BUCKET
  ```

## ☑️ Phase 3: Model Training

### Local Training
- [ ] Start MLflow UI: `mlflow ui --port 5000` (in separate terminal)
- [ ] Train model locally:
  ```bash
  python train_model.py \
    --train-csv processed/train.csv \
    --val-csv processed/val.csv \
    --n-estimators 100
  ```
- [ ] Verify `model.joblib` was created
- [ ] Verify `metrics.json` was created
- [ ] Check MLflow UI at `http://localhost:5000`
- [ ] Review experiment metrics and parameters

### Model Packaging
- [ ] Package model for deployment:
  ```bash
  python train_model.py \
    --train-csv processed/train.csv \
    --val-csv processed/val.csv \
    --package \
    --s3-bucket $S3_BUCKET
  ```
- [ ] Verify `model.tar.gz` was uploaded to S3
- [ ] Check S3 bucket: `aws s3 ls s3://$S3_BUCKET/models/`

## ☑️ Phase 4: Deployment (Optional - requires AWS resources)

### SageMaker Deployment
- [ ] Ensure ECR image exists (or use pre-built SageMaker image)
- [ ] Verify S3 bucket contains model: `aws s3 ls s3://$S3_BUCKET/models/model.tar.gz`
- [ ] Run deployment script: `python deploy.py`
- [ ] Wait for endpoint creation (5-10 minutes)
- [ ] Check endpoint status:
  ```bash
  aws sagemaker describe-endpoint --endpoint-name mlops-endpoint
  ```
- [ ] Verify endpoint is InService

### Test Inference (Optional)
- [ ] Create test payload
- [ ] Invoke endpoint:
  ```bash
  aws sagemaker-runtime invoke-endpoint \
    --endpoint-name mlops-endpoint \
    --content-type text/csv \
    --body "data" output.json
  ```
- [ ] Verify predictions are reasonable

## ☑️ Phase 5: Monitoring

### Drift Detection Setup
- [ ] Create reference dataset (use training data)
- [ ] Collect current production data (or simulate with validation data)
- [ ] Run drift detection:
  ```bash
  python drift_detection.py \
    --reference-csv processed/train.csv \
    --current-csv processed/val.csv
  ```
- [ ] Open `drift_report.html` in browser
- [ ] Review drift metrics
- [ ] Check `drift_results.json`

### Alerting Setup (Optional)
- [ ] Create SNS topic: `aws sns create-topic --name mlops-alerts`
- [ ] Subscribe email to topic
- [ ] Set `SNS_TOPIC_ARN` in `.env`
- [ ] Test alerting:
  ```bash
  python drift_detection.py \
    --reference-csv processed/train.csv \
    --current-csv processed/val.csv \
    --alert-sns --threshold 0.1
  ```
- [ ] Verify email alert received

## ☑️ Phase 6: CI/CD (Optional)

### Terraform Infrastructure
- [ ] Navigate to terraform directory: `cd terraform/codepipeline`
- [ ] Review `terraform.tfvars.example`
- [ ] Create `terraform.tfvars` with your values
- [ ] Initialize: `terraform init`
- [ ] Plan: `terraform plan`
- [ ] Apply: `terraform apply`
- [ ] Verify resources in AWS Console

### GitHub Actions
- [ ] Go to GitHub repository settings
- [ ] Navigate to Secrets and Variables > Actions
- [ ] Add secrets:
  - `AWS_REGION`
  - `S3_BUCKET`
  - `ECR_IMAGE`
  - `SAGEMAKER_ROLE_ARN`
- [ ] Push code to trigger pipeline
- [ ] Monitor Actions tab in GitHub

## ☑️ Phase 7: Production Checklist

### Security
- [ ] Review IAM roles and policies
- [ ] Ensure least privilege access
- [ ] Enable S3 bucket versioning
- [ ] Enable S3 bucket encryption
- [ ] Set up VPC endpoints (if needed)
- [ ] Review security group rules
- [ ] Enable CloudTrail logging

### Monitoring
- [ ] Set up CloudWatch dashboards
- [ ] Create CloudWatch alarms for:
  - [ ] Endpoint latency
  - [ ] Endpoint errors
  - [ ] Model drift
  - [ ] Cost anomalies
- [ ] Configure SNS notifications
- [ ] Test alert delivery

### Documentation
- [ ] Review `readme.md` for architecture
- [ ] Review `IMPROVEMENTS.md` for changes
- [ ] Review `QUICKSTART.md` for commands
- [ ] Document any custom configurations
- [ ] Update environment-specific settings

### Testing
- [ ] Run full test suite: `pytest --cov=.`
- [ ] Verify coverage >80%
- [ ] Test preprocessing with production-like data
- [ ] Test model training end-to-end
- [ ] Test deployment in staging environment
- [ ] Run drift detection with real data

## ☑️ Troubleshooting

If you encounter issues:

### Common Issues
- [ ] **Import errors**: Activate virtual environment
- [ ] **AWS credentials**: Run `aws configure`
- [ ] **MLflow errors**: Check if server is running
- [ ] **S3 access denied**: Verify IAM permissions
- [ ] **Terraform errors**: Check region and account ID

### Getting Help
- [ ] Check `QUICKSTART.md` troubleshooting section
- [ ] Review error messages in stderr
- [ ] Check CloudWatch logs for deployment issues
- [ ] Verify all environment variables in `.env`
- [ ] Run tests to isolate issues: `pytest -v`

## 📊 Success Criteria

You've successfully set up the pipeline when:
- ✅ All tests pass locally
- ✅ Model can be trained and logged to MLflow
- ✅ Drift detection generates reports
- ✅ (Optional) Model deploys to SageMaker
- ✅ (Optional) CI/CD pipeline executes successfully

## 🎉 Next Steps After Setup

1. **Experiment with hyperparameters**: Try different `n_estimators` values
2. **Monitor drift**: Set up regular drift detection jobs
3. **Automate retraining**: Create EventBridge rule for drift alerts
4. **Scale up**: Deploy to production SageMaker endpoints
5. **Customize**: Adapt pipeline for your own datasets

## 📚 Reference Documents

- **Architecture**: See `readme.md`
- **Improvements**: See `IMPROVEMENTS.md`
- **Quick Commands**: See `QUICKSTART.md`
- **Summary**: See `SUMMARY.md`

---

**Happy MLOps-ing! 🚀**

For questions or issues, review the documentation files or check the inline code comments.
