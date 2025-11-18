## 🧠 Comprehensive AWS MLOps Project Guide

End-to-End ML Pipeline Deployment with Amazon SageMaker, CloudWatch, MLflow, and Evidently AI

This guide provides a detailed, hands-on walkthrough for building, deploying, and monitoring a complete ML lifecycle with AWS SageMaker. It includes automated deployment to SageMaker Endpoints, CI/CD integration, CloudWatch Monitoring, and Evidently AI or Deequ-based drift detection.

## 🚀 Architecture Overview

![Project architectural diagram](screenshots/AWS_MLOPS_Project_diagram.png)

## Prerequisites & variables

Before you begin, set these variables or replace placeholders in commands and scripts below:

- AWS account with permissions to create S3, SageMaker, IAM roles, ECR, CloudWatch, EventBridge and Lambda
- REGION (e.g. us-east-1)
- ACCOUNT_ID (your 12-digit AWS account id)
- S3_BUCKET (e.g. mlops-demo-pipeline-bucket) — must be globally unique
- SAGEMAKER_ROLE_ARN (ARN of an IAM role with SageMaker permissions)
- SNS_TOPIC_ARN (optional — for alarms/notifications)
- ECR_IMAGE (ECR image URI for serving container)

Install these Python packages for the examples (also provided in `requirements.txt`).

### Recommended: Use a Virtual Environment

To avoid permission issues and keep project dependencies isolated, it's highly recommended to use a virtual environment.

1.  **Create and activate the environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

    _(Your shell prompt will change to show you're in the `(venv)` environment.)_

2.  **Install the requirements:**
    ```bash
    pip install -r requirements.txt
    ```

All packages will be installed inside the `./venv` directory. Remember to activate the environment whenever you open a new terminal session to work on the project.

## ⚙️ Step-by-Step Implementation

### Step 1: Setup Your AWS Environment

Create required AWS resources. Replace placeholders (ACCOUNT_ID, SAGEMAKER_ROLE_ARN, S3_BUCKET, REGION) before running.

```bash
aws s3 mb s3://$S3_BUCKET --region $REGION
aws sagemaker create-notebook-instance --notebook-instance-name mlops-instance \
  --instance-type ml.t3.medium \
  --role $SAGEMAKER_ROLE_ARN
```

Enable versioning for the bucket:

```bash
aws s3api put-bucket-versioning --bucket $S3_BUCKET --versioning-configuration Status=Enabled
```

Push raw data to `s3://$S3_BUCKET/raw/`.

### Step 2: Data Preprocessing (AWS Glue or Airflow)

ETL with Airflow DAG (local or Amazon MWAA) to clean and store processed data.

Store clean output in `s3://$S3_BUCKET/processed/`.

We provide a small preprocessing helper for the Telco Customer Churn dataset:

`preprocess_telco.py` — cleans dtypes, encodes categorical variables, performs a train/validation split, and writes `train.csv` and `val.csv` to a local `./processed` directory. It can also upload the processed CSVs to `s3://<bucket>/processed/` when run with `--upload` and `--s3-bucket`.

Example usage (local):

```bash
python preprocess_telco.py --input-csv ~/Downloads/WA_Fn-UseC_-Telco-Customer-Churn.csv --output-dir ./processed
```

Example usage (upload to S3):

```bash
python preprocess_telco.py --input-csv ~/Downloads/WA_Fn-UseC_-Telco-Customer-Churn.csv --upload --s3-bucket my-mlops-bucket
```

After running, the pipeline expects processed data at `s3://$S3_BUCKET/processed/` or locally at `./processed/` for training.

### Step 3: Model Training and Experiment Tracking

Using Amazon SageMaker SDK (example uses SKLearn estimator and `train_model.py`):

```python
from sagemaker.sklearn.estimator import SKLearn
from sagemaker import get_execution_role, Session

role = get_execution_role()
sess = Session()

sklearn_estimator = SKLearn(
	entry_point='train_model.py',
	role=role,
	instance_type='ml.m5.xlarge',
	source_dir='src',
	framework_version='1.0-1'
)
sklearn_estimator.fit({'train': f's3://{S3_BUCKET}/processed/'})
```

Track experiments with MLflow by integrating it into SageMaker’s callback logger.

### Step 4: Register Model in SageMaker Model Registry

After training, store your model:

```python
model = sklearn_estimator.create_model(
	name='mlops-model-v1',
	role=role
)
model_package_arn = model.register(
	content_types=['text/csv'], response_types=['text/csv'],
	inference_instances=['ml.m5.large'], transform_instances=['ml.m5.xlarge']
)
```

### Step 5: CI/CD Pipelines (Automated Build & Deploy)

We recommend using AWS CodePipeline as the primary CI/CD orchestrator for this project. CodePipeline integrates natively with other AWS services (CodeCommit, CodeBuild, ECR, SageMaker, CloudWatch, SNS) and simplifies permission management within your AWS account.

Typical pipeline stages:

- Source: CodeCommit or GitHub (store your repo here; if using GitHub, connect via a GitHub token or the GitHub App integration).
- Build: CodeBuild builds artifacts, runs tests, packages the model or container, and pushes images to ECR.
- Deploy: CodeBuild or a custom action that invokes `deploy.py`/boto3 to create/update SageMaker Model and Endpoint (or use SageMaker Pipelines for model package promotion).
- Optional: Manual approval or automated validation (smoke tests) before promoting to production.

Key resources you'll use:

- CodePipeline pipeline
- CodeBuild project(s) with a build role that can read/write S3, push to ECR, and call SageMaker APIs
- S3 artifact bucket (for pipeline artifacts)
- IAM roles for CodePipeline/CodeBuild with least-privilege policies (see `docs/iam/sagemaker_role_policy.json` as a starting point)

Example CodeBuild `buildspec.yml` (used in the Build/Deploy stage to install dependencies and run the deploy script):

```yaml
version: 0.2
phases:
	install:
		runtime-versions:
			python: 3.10
		commands:
			- python -m pip install --upgrade pip
			- pip install -r requirements.txt
	build:
		commands:
			- echo "Running deployment script"
			- python deploy.py
artifacts:
	files:
		- '**/*'
	discard-paths: yes
```

How to create the pipeline (overview):

1. Create or choose an S3 bucket for pipeline artifacts.
2. Create a CodeBuild project with the above `buildspec.yml` (or store it in your repo at `buildspec.yml`).
3. Create a CodePipeline pipeline that uses your source provider (CodeCommit, GitHub) and the CodeBuild project as the Build/Deploy stage. Configure an IAM role for the pipeline that allows CodeBuild to assume the necessary permissions.
4. Grant the CodeBuild role permissions to push to ECR (if building containers), access S3 artifacts, and call SageMaker/CreateModel/CreateEndpoint. Use least privilege — see `docs/iam/sagemaker_role_policy.json` as a starting example.

You can create the pipeline using CloudFormation, the AWS Console, or the AWS CLI. For a simple test pipeline, you can create a CodeBuild project that runs on pushes to your repository (via webhook or CodePipeline) and runs `deploy.py` to perform the deployment step.

Notes:

- If your source repository is GitHub and you prefer an external CI provider for development branches, you can still use CodePipeline for production deployments by connecting the GitHub repo as the pipeline source.
- For complex model promotion workflows, consider integrating SageMaker Pipelines to handle training, model evaluation, model registry, and promotion; then trigger SageMaker Pipeline executions from CodePipeline.
- Ensure secrets and AWS credentials are stored in AWS Secrets Manager or passed via the CodeBuild project's environment variables and not committed to source.

### Step 6: Deploy Model to SageMaker Endpoints

Create SageMaker Model (example uses placeholders — replace with your `ECR_IMAGE` and `S3_BUCKET` paths):

```python
import boto3

sm = boto3.client('sagemaker')

model_name = 'mlops-model-v1'
container = {
	'Image': ECR_IMAGE,
	'ModelDataUrl': f's3://{S3_BUCKET}/models/model.tar.gz'
}

sm.create_model(
	ModelName=model_name,
	ExecutionRoleArn=SAGEMAKER_ROLE_ARN,
	PrimaryContainer=container
)
```

Deploy Endpoint:

```python
endpoint_config_name = 'mlops-endpoint-config'
endpoint_name = 'mlops-endpoint'

sm.create_endpoint_config(
	EndpointConfigName=endpoint_config_name,
	ProductionVariants=[
		{
			'VariantName': 'AllTraffic',
			'ModelName': model_name,
			'InitialInstanceCount': 1,
			'InstanceType': 'ml.m5.large'
		}
	]
)
sm.create_endpoint(
	EndpointName=endpoint_name,
	EndpointConfigName=endpoint_config_name
)
```

Test Inference Endpoint:

```python
import boto3, json
runtime = boto3.client('sagemaker-runtime')

payload = json.dumps({"age": 34, "tenure": 5, "usage": 200})
response = runtime.invoke_endpoint(
	EndpointName='mlops-endpoint',
	ContentType='application/json',
	Body=payload
)
print(response['Body'].read())
```

✅ Optionally: Use Serverless Endpoint (saves cost for low-traffic apps).

### Step 7: Monitoring, Logging, and Drift Detection

#### A. CloudWatch Integration

SageMaker automatically logs invocation count, latency metrics and model error rates. View under Metrics → SageMaker → EndpointInvocation in the CloudWatch console.

Enable event alerts (replace SNS_TOPIC_ARN):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "HighLatencyAlarm" \
  --metric-name "ModelLatency" \
  --namespace "AWS/SageMaker" \
  --statistic "Average" \
  --threshold 1000 \
  --comparison-operator "GreaterThanThreshold" \
  --period 60 \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC_ARN
```

#### B. Model Drift Monitoring (SageMaker Model Monitor)

Capture endpoint data:

```python
sm.create_data_capture_config(
	EnableCapture=True,
	CaptureOptions=[{'CaptureMode': 'Input'}],
	DestinationS3Uri=f's3://{S3_BUCKET}/data-capture/'
)
```

#### C. EvidentlyAI Integration

Use Evidently in a Lambda or Airflow batch job:

```python
from evidently.report import Report
from evidently.metrics import DataDriftPreset

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=train_df, current_data=live_df)
report.save_html("data_drift_report.html")
```

#### D. AWS Deequ Option

Use AWS Deequ for data validation (Spark/pydeequ example):

```python
from pydeequ.checks import Check
from pydeequ.verification import VerificationSuite

check = Check(spark, CheckLevel.Warning, "DataQuality") \
	.isComplete("user_id") \
	.hasMin("age", lambda x: x >= 0)

results = VerificationSuite(spark) \
	.onData(df) \
	.addCheck(check) \
	.run()
```

### Step 8: Auto-Retraining & Feedback Loop

Use EventBridge rules to trigger retraining job when drift exceeds threshold. Update model via SageMaker Pipelines → rebuild endpoint → notify via SNS.

📊 Final Outcome

- Automated ML Pipeline
- Deployed Model Endpoint (https://runtime.sagemaker.$REGION.amazonaws.com/...)
- CloudWatch Dashboards for Monitoring
- Automatic Drift Detection + Retraining Trigger

🧭 Next Steps

- Integrate Terraform for multi-cloud portability (reuse modules for GCP/Azure).
- Add EvidentlyAI & Deequ jobs as nightly checks.
- Add real-time rolling updates using SageMaker endpoint variants.
- Publish the project as an open-source portfolio piece on GitHub with README.md + architecture diagram.
