"""Configuration loader for MLOps pipeline.

Loads configuration from environment variables with support for .env files.
Priority: environment variables > .env file > defaults
"""

import os
from typing import Optional
from pathlib import Path


def load_env_file(env_file: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    env_path = Path(env_file)
    if not env_path.exists():
        return
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


class Config:
    """Configuration manager for MLOps pipeline."""
    
    def __init__(self, load_dotenv: bool = True):
        """Initialize configuration.
        
        Args:
            load_dotenv: Whether to load .env file (default: True)
        """
        if load_dotenv:
            load_env_file()
    
    # AWS Configuration
    @property
    def aws_region(self) -> str:
        return os.environ.get('AWS_REGION', 'us-east-1')
    
    @property
    def aws_account_id(self) -> Optional[str]:
        return os.environ.get('AWS_ACCOUNT_ID')
    
    # S3 Configuration
    @property
    def s3_bucket(self) -> Optional[str]:
        return os.environ.get('S3_BUCKET')
    
    @property
    def s3_key(self) -> str:
        return os.environ.get('S3_KEY', 'models/model.tar.gz')
    
    # SageMaker Configuration
    @property
    def sagemaker_role_arn(self) -> Optional[str]:
        return os.environ.get('SAGEMAKER_ROLE_ARN')
    
    @property
    def model_name(self) -> str:
        return os.environ.get('MODEL_NAME', 'mlops-model-v1')
    
    @property
    def endpoint_name(self) -> str:
        return os.environ.get('ENDPOINT_NAME', 'mlops-endpoint')
    
    # ECR Configuration
    @property
    def ecr_image(self) -> Optional[str]:
        return os.environ.get('ECR_IMAGE')
    
    # SNS Configuration
    @property
    def sns_topic_arn(self) -> Optional[str]:
        return os.environ.get('SNS_TOPIC_ARN')
    
    # MLflow Configuration
    @property
    def mlflow_tracking_uri(self) -> str:
        return os.environ.get('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    
    @property
    def mlflow_experiment_name(self) -> str:
        return os.environ.get('MLFLOW_EXPERIMENT_NAME', 'telco-churn-prediction')
    
    # Monitoring Configuration
    @property
    def enable_drift_detection(self) -> bool:
        return os.environ.get('ENABLE_DRIFT_DETECTION', 'false').lower() == 'true'
    
    @property
    def drift_threshold(self) -> float:
        return float(os.environ.get('DRIFT_THRESHOLD', '0.3'))
    
    def validate(self) -> list[str]:
        """Validate required configuration values.
        
        Returns:
            List of missing required configuration keys
        """
        missing = []
        required_fields = {
            'S3_BUCKET': self.s3_bucket,
            'SAGEMAKER_ROLE_ARN': self.sagemaker_role_arn,
            'ECR_IMAGE': self.ecr_image,
        }
        
        for key, value in required_fields.items():
            if not value:
                missing.append(key)
        
        return missing
    
    def __repr__(self) -> str:
        """String representation (hides sensitive values)."""
        return (
            f"Config(region={self.aws_region}, "
            f"bucket={self.s3_bucket}, "
            f"model={self.model_name}, "
            f"endpoint={self.endpoint_name})"
        )


# Global config instance
config = Config()
