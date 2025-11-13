"""deploy.py
Small utility to create a SageMaker Model and Endpoint from an existing model artifact stored in S3.
Reads configuration from environment variables or defaults and performs basic validation.
"""

import os
import time
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_KEY = os.environ.get('S3_KEY', 'models/model.tar.gz')
MODEL_NAME = os.environ.get('MODEL_NAME', 'mlops-model-v1')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME', 'mlops-endpoint')
ECR_IMAGE = os.environ.get('ECR_IMAGE')
SAGEMAKER_ROLE_ARN = os.environ.get('SAGEMAKER_ROLE_ARN')

if not S3_BUCKET or not ECR_IMAGE or not SAGEMAKER_ROLE_ARN:
    print("Required environment variables missing. Set S3_BUCKET, ECR_IMAGE, and SAGEMAKER_ROLE_ARN.")
    raise SystemExit(1)

sm = boto3.client('sagemaker', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)


def s3_object_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def create_model():
    model_data_url = f's3://{S3_BUCKET}/{S3_KEY}'
    container = {
        'Image': ECR_IMAGE,
        'ModelDataUrl': model_data_url
    }
    print(f"Creating SageMaker model {MODEL_NAME} using {model_data_url}")
    try:
        sm.create_model(ModelName=MODEL_NAME, ExecutionRoleArn=SAGEMAKER_ROLE_ARN, PrimaryContainer=container)
        print(f"Created model {MODEL_NAME}")
    except ClientError as e:
        print("create_model error:", e)
        raise


def create_endpoint():
    endpoint_config_name = f"{ENDPOINT_NAME}-config"
    print(f"Creating endpoint config {endpoint_config_name}")
    try:
        sm.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[{
                'VariantName': 'AllTraffic',
                'ModelName': MODEL_NAME,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.m5.large'
            }]
        )
        print(f"Creating endpoint {ENDPOINT_NAME}")
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=endpoint_config_name)
    except ClientError as e:
        print("create_endpoint error:", e)
        raise


def wait_for_endpoint(endpoint_name, timeout=900, poll_interval=15):
    elapsed = 0
    while elapsed < timeout:
        resp = sm.describe_endpoint(EndpointName=endpoint_name)
        status = resp['EndpointStatus']
        print(f"Endpoint {endpoint_name} status: {status}")
        if status in ('InService', 'Failed'):
            return status
        time.sleep(poll_interval)
        elapsed += poll_interval
    return 'Timeout'


if __name__ == '__main__':
    # ensure model artifact exists in S3
    if not s3_object_exists(S3_BUCKET, S3_KEY):
        print(f"Model artifact not found at s3://{S3_BUCKET}/{S3_KEY}. Upload the model tar.gz first.")
        raise SystemExit(1)

    create_model()
    create_endpoint()
    status = wait_for_endpoint(ENDPOINT_NAME)
    print(f"Endpoint final status: {status}")
