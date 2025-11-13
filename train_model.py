"""train_model.py
Simple training script that reads CSV training data, trains a scikit-learn model,
saves it locally and can optionally package and upload the model artifact to S3.

This is a convenience stub for demos and CI; replace with your real training/feature logic.
"""

import argparse
import os
import tarfile
import tempfile
import boto3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib


def package_model(output_model_path, tar_path):
    # Create a tar.gz containing the model file
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(output_model_path, arcname=os.path.basename(output_model_path))


def upload_to_s3(tar_path, bucket, key, region=None):
    s3 = boto3.client('s3', region_name=region) if region else boto3.client('s3')
    s3.upload_file(tar_path, bucket, key)


def main(args):
    # Read input CSV if provided, otherwise use example data
    if args.input_csv and os.path.exists(args.input_csv):
        df = pd.read_csv(args.input_csv)
        # naive split: last column is label
        X = df.iloc[:, :-1]
        y = df.iloc[:, -1]
    else:
        X = pd.DataFrame({"age": [20, 30, 40], "tenure": [1, 2, 3], "usage": [100, 200, 300]})
        y = [0, 1, 0]

    model = RandomForestClassifier(n_estimators=10)
    model.fit(X, y)

    os.makedirs(os.path.dirname(args.output_model), exist_ok=True) if os.path.dirname(args.output_model) else None
    joblib.dump(model, args.output_model)
    print(f"Saved model to {args.output_model}")

    # optionally create tar.gz and upload
    if args.package and args.s3_bucket:
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = os.path.join(tmpdir, args.tar_name)
            package_model(args.output_model, tar_path)
            s3_key = f"models/{os.path.basename(tar_path)}"
            upload_to_s3(tar_path, args.s3_bucket, s3_key, region=args.aws_region)
            print(f"Uploaded {tar_path} to s3://{args.s3_bucket}/{s3_key}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-csv', type=str, default=None, help='Optional input CSV for training')
    parser.add_argument('--output-model', type=str, default='model.joblib', help='Local path to save trained model')
    parser.add_argument('--package', action='store_true', help='Create a tar.gz of the model and upload to S3')
    parser.add_argument('--tar-name', type=str, default='model.tar.gz', help='Name of the packaged tar.gz')
    parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket to upload the packaged model')
    parser.add_argument('--aws-region', type=str, default=None, help='AWS region for S3 client (optional)')
    args = parser.parse_args()
    main(args)
