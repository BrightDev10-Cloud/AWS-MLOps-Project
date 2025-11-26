# Quick Reference Guide

This document provides quick commands for common MLOps tasks.

## Initial Setup

```bash
# 1. Clone repository (if not already done)
git clone <your-repo-url>
cd AWS_MLOps_Project

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Edit with your AWS credentials and settings

# 5. Verify setup with tests
pytest -v
```

## Data Preprocessing

```bash
# Preprocess Telco dataset locally
python preprocess_telco.py \
  --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
  --output-dir processed \
  --test-size 0.2

# Preprocess and upload to S3
python preprocess_telco.py \
  --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
  --output-dir processed \
  --upload \
  --s3-bucket $S3_BUCKET
```

## Model Training

```bash
# Train locally
python train_model.py \
  --train-csv processed/train.csv \
  --val-csv processed/val.csv \
  --n-estimators 100

# Train and package for S3
python train_model.py \
  --train-csv processed/train.csv \
  --val-csv processed/val.csv \
  --n-estimators 100 \
  --package \
  --s3-bucket $S3_BUCKET \
  --aws-region $AWS_REGION

# View MLflow experiments
mlflow ui --port 5000
# Then open http://localhost:5000 in browser
```

## Deployment

```bash
# Deploy model to SageMaker
# (Ensure .env is configured with proper credentials)
python deploy.py

# Check deployment status
aws sagemaker describe-endpoint --endpoint-name mlops-endpoint
```

## Monitoring

```bash
# Run drift detection
python drift_detection.py \
  --reference-csv processed/train.csv \
  --current-csv production/current_data.csv \
  --output-html drift_report.html

# Run drift detection with alerts
python drift_detection.py \
  --reference-csv processed/train.csv \
  --current-csv production/current_data.csv \
  --s3-bucket $S3_BUCKET \
  --alert-sns \
  --threshold 0.3

# View drift report
open drift_report.html  # On macOS
# On Linux: xdg-open drift_report.html
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report

# Run specific test file
pytest tests/test_preprocess.py -v

# Run specific test
pytest tests/test_preprocess.py::TestCleanTelco::test_removes_customer_id -v
```

## AWS Infrastructure

```bash
# Initialize Terraform
cd terraform/codepipeline
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure
terraform apply

# Destroy infrastructure
terraform destroy
```

## Common Workflows

### Complete Local Pipeline
```bash
# 1. Preprocess data
python preprocess_telco.py \
  --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
  --output-dir processed

# 2. Train model
python train_model.py \
  --train-csv processed/train.csv \
  --val-csv processed/val.csv \
  --n-estimators 100

# 3. Run tests
pytest

# 4. Check drift (optional, needs current production data)
# python drift_detection.py --reference-csv processed/train.csv --current-csv current.csv
```

### Deploy to AWS
```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your AWS credentials

# 2. Preprocess and upload
python preprocess_telco.py \
  --input-csv WA_Fn-UseC_-Telco-Customer-Churn.csv \
  --upload \
  --s3-bucket $S3_BUCKET

# 3. Train and package
python train_model.py \
  --train-csv processed/train.csv \
  --val-csv processed/val.csv \
  --package \
  --s3-bucket $S3_BUCKET

# 4. Deploy to SageMaker
python deploy.py

# 5. Verify deployment
aws sagemaker describe-endpoint --endpoint-name mlops-endpoint
```

### CI/CD with GitHub Actions
```bash
# Push to trigger pipeline
git add .
git commit -m "Update model training"
git push origin main

# Check workflow status
# Visit: https://github.com/<your-repo>/actions
```

## Useful AWS CLI Commands

```bash
# List S3 bucket contents
aws s3 ls s3://$S3_BUCKET/ --recursive

# Download model from S3
aws s3 cp s3://$S3_BUCKET/models/model.tar.gz ./

# Check SageMaker endpoint status
aws sagemaker describe-endpoint --endpoint-name mlops-endpoint

# View CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/mlops-endpoint --follow

# Create SNS topic for alerts
aws sns create-topic --name mlops-alerts

# Subscribe to SNS topic (email)
aws sns subscribe \
  --topic-arn arn:aws:sns:$AWS_REGION:$ACCOUNT_ID:mlops-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Troubleshooting

### MLflow Not Starting
```bash
# Start MLflow server
mlflow server --host 0.0.0.0 --port 5000

# If port is busy
lsof -ti:5000 | xargs kill -9
mlflow server --host 0.0.0.0 --port 5000
```

### AWS Credentials Not Found
```bash
# Configure AWS CLI
aws configure

# Or set in .env file
echo "AWS_ACCESS_KEY_ID=your_key" >> .env
echo "AWS_SECRET_ACCESS_KEY=your_secret" >> .env
```

### Import Errors in Tests
```bash
# Make sure you're in project root
cd /path/to/AWS_MLOps_Project

# Install in development mode
pip install -e .

# Or update PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### Terraform State Issues
```bash
# Refresh state
terraform refresh

# Import existing resource
terraform import aws_s3_bucket.artifacts my-bucket-name

# Remove from state (doesn't delete resource)
terraform state rm aws_s3_bucket.artifacts
```

## Environment Variables Reference

Required in `.env`:
```bash
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
SAGEMAKER_ROLE_ARN=arn:aws:iam::123456789012:role/SageMakerRole
ECR_IMAGE=123456789012.dkr.ecr.us-east-1.amazonaws.com/mlops:latest
```

Optional:
```bash
MODEL_NAME=mlops-model-v1
ENDPOINT_NAME=mlops-endpoint
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:mlops-alerts
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=telco-churn-prediction
ENABLE_DRIFT_DETECTION=true
DRIFT_THRESHOLD=0.3
```

## Performance Tips

1. **Use smaller n_estimators for testing**: `--n-estimators 10`
2. **Cache preprocessed data**: Save to `processed/` directory
3. **Use ml.t3.medium for development**: Cheaper SageMaker instances
4. **Enable S3 versioning**: Rollback capability for models
5. **Set up CloudWatch alarms**: Monitor costs and performance

## Next Steps

- See `IMPROVEMENTS.md` for recent enhancements
- See `readme.md` for detailed architecture
- Check `tests/` for usage examples
- Review `.env.example` for all configuration options
