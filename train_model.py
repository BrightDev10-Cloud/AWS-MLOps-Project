"""train_model.py
Training script that reads CSV training data, trains a scikit-learn model,
saves it locally and can optionally package and upload the model artifact to S3.
Includes MLflow experiment tracking for model versioning and metrics logging.
"""

import argparse
import json
import os
import sys
import tarfile
import tempfile
import boto3
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
from config import config


def package_model(output_model_path, tar_path):
    # Create a tar.gz containing the model file
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(output_model_path, arcname=os.path.basename(output_model_path))


def upload_to_s3(tar_path, bucket, key, region=None):
    s3 = boto3.client('s3', region_name=region) if region else boto3.client('s3')
    s3.upload_file(tar_path, bucket, key)


def main(args):
    # Set up MLflow
    mlflow.set_tracking_uri(config.mlflow_tracking_uri)
    mlflow.set_experiment(config.mlflow_experiment_name)
    
    # Read processed train/val CSVs
    train_path = args.train_csv if args.train_csv else os.path.join('processed', 'train.csv')
    val_path = args.val_csv if args.val_csv else os.path.join('processed', 'val.csv')

    if os.path.exists(train_path) and os.path.exists(val_path):
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        # assume target column is named 'Churn' (0/1)
        if 'Churn' not in train_df.columns:
            raise ValueError("Expected 'Churn' column in training CSV after preprocessing")
        X_train = train_df.drop(columns=['Churn'])
        y_train = train_df['Churn']
        X_val = val_df.drop(columns=['Churn'])
        y_val = val_df['Churn']
    else:
        # fallback to small example data
        print("Warning: Training/validation CSVs not found, using fallback example data", file=sys.stderr)
        X_train = pd.DataFrame({"age": [20, 30, 40], "tenure": [1, 2, 3], "usage": [100, 200, 300]})
        y_train = [0, 1, 0]
        X_val = X_train
        y_val = y_train

    # Start MLflow run
    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("n_estimators", args.n_estimators)
        mlflow.log_param("random_state", 42)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("val_samples", len(X_val))
        
        # Train model
        model = RandomForestClassifier(n_estimators=args.n_estimators, random_state=42)
        model.fit(X_train, y_train)

        # predictions and metrics on validation set
        preds = model.predict(X_val)
        metrics = {
            'accuracy': float(accuracy_score(y_val, preds)),
            'precision': float(precision_score(y_val, preds, zero_division=0)),
            'recall': float(recall_score(y_val, preds, zero_division=0)),
            'f1': float(f1_score(y_val, preds, zero_division=0))
        }

        # Log metrics to MLflow
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        # ensure output directory
        out_dir = os.path.dirname(args.output_model) or '.'
        os.makedirs(out_dir, exist_ok=True)

        # save model locally
        joblib.dump(model, args.output_model)
        print(f"✓ Saved model to {args.output_model}")

        # Log model to MLflow
        mlflow.sklearn.log_model(model, "model")

        # save metrics alongside model
        metrics_path = args.metrics_path if args.metrics_path else os.path.join(out_dir, 'metrics.json')
        with open(metrics_path, 'w') as fh:
            json.dump(metrics, fh, indent=2)
        print(f"✓ Saved metrics to {metrics_path}")
        
        # Log metrics file as artifact
        mlflow.log_artifact(metrics_path)

        print("Validation metrics:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")

        # optionally create tar.gz and upload
        if args.package and args.s3_bucket:
            with tempfile.TemporaryDirectory() as tmpdir:
                tar_path = os.path.join(tmpdir, args.tar_name)
                # include the model and metrics in the tarball
                with tarfile.open(tar_path, 'w:gz') as tar:
                    tar.add(args.output_model, arcname=os.path.basename(args.output_model))
                    tar.add(metrics_path, arcname=os.path.basename(metrics_path))
                s3_key = f"models/{os.path.basename(tar_path)}"
                upload_to_s3(tar_path, args.s3_bucket, s3_key, region=args.aws_region)
                print(f"✓ Uploaded {tar_path} to s3://{args.s3_bucket}/{s3_key}")
                
                # Log S3 URI to MLflow
                mlflow.log_param("s3_model_uri", f"s3://{args.s3_bucket}/{s3_key}")
        
        # Log run info
        run_id = mlflow.active_run().info.run_id
        print(f"✓ MLflow run completed: {run_id}")
        
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-csv', type=str, default=None, help='Path to processed train CSV (default: processed/train.csv)')
    parser.add_argument('--val-csv', type=str, default=None, help='Path to processed val CSV (default: processed/val.csv)')
    parser.add_argument('--output-model', type=str, default='model.joblib', help='Local path to save trained model')
    parser.add_argument('--metrics-path', type=str, default=None, help='Path to write metrics JSON (default: same dir as model)')
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of trees for RandomForest')
    parser.add_argument('--package', action='store_true', help='Create a tar.gz of the model+metrics and upload to S3')
    parser.add_argument('--tar-name', type=str, default='model.tar.gz', help='Name of the packaged tar.gz')
    parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket to upload the packaged model')
    parser.add_argument('--aws-region', type=str, default=None, help='AWS region for S3 client (optional)')
    args = parser.parse_args()
    
    try:
        sys.exit(main(args))
    except Exception as e:
        print(f"✗ Training failed: {e}", file=sys.stderr)
        sys.exit(1)
