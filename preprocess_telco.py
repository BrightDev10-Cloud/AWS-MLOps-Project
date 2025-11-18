"""Preprocess Telco Customer Churn dataset.

Reads raw CSV, cleans dtypes, encodes categoricals, splits into train/validation,
saves CSVs locally and optionally uploads to s3://<bucket>/processed/.

Usage examples:
  python preprocess_telco.py --input-csv /path/WA_Fn-UseC_-Telco-Customer-Churn.csv --output-dir ./processed
  python preprocess_telco.py --input-csv /path/WA_Fn-UseC_-Telco-Customer-Churn.csv --s3-bucket my-bucket --upload
"""

import argparse
import os
import boto3
import pandas as pd
from sklearn.model_selection import train_test_split


def clean_telco(df: pd.DataFrame) -> pd.DataFrame:
    # Drop identifier
    if 'customerID' in df.columns:
        df = df.drop(columns=['customerID'])

    # Strip whitespace from string columns
    obj_cols = df.select_dtypes(include=['object']).columns
    for c in obj_cols:
        df[c] = df[c].str.strip()

    # Convert TotalCharges to numeric (some rows are empty strings)
    if 'TotalCharges' in df.columns:
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')

    # Fill numeric NaNs with 0 or median
    for num in df.select_dtypes(include=['float64', 'int64']).columns:
        if df[num].isnull().any():
            df[num] = df[num].fillna(df[num].median())

    # Binary mapping for common Yes/No columns
    yes_no_cols = [c for c in df.columns if df[c].dtype == 'object' and df[c].isin(['Yes', 'No']).any()]
    for c in yes_no_cols:
        df[c] = df[c].map({'Yes': 1, 'No': 0}).fillna(df[c])

    # Target column mapping
    if 'Churn' in df.columns:
        df['Churn'] = df['Churn'].map({'Yes': 1, 'No': 0})

    # One-hot encode remaining categorical object columns
    remaining_obj = df.select_dtypes(include=['object']).columns.tolist()
    if remaining_obj:
        df = pd.get_dummies(df, columns=remaining_obj, drop_first=True)

    return df


def upload_file(s3_client, local_path, bucket, key):
    s3_client.upload_file(local_path, bucket, key)
    print(f"Uploaded {local_path} to s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description='Preprocess Telco Churn CSV and optionally upload to S3')
    parser.add_argument('--input-csv', required=True, help='Path to raw Telco CSV')
    parser.add_argument('--output-dir', default='processed', help='Local output directory for processed CSVs')
    parser.add_argument('--test-size', type=float, default=0.2, help='Validation fraction')
    parser.add_argument('--random-state', type=int, default=42)
    parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket to upload processed CSVs (optional)')
    parser.add_argument('--upload', action='store_true', help='Upload processed CSVs to S3 if s3-bucket provided')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading {args.input_csv}...")
    df = pd.read_csv(args.input_csv)
    print(f"Initial shape: {df.shape}")

    df_clean = clean_telco(df)
    print(f"After cleaning shape: {df_clean.shape}")

    target = 'Churn' if 'Churn' in df_clean.columns else None
    if target:
        X = df_clean.drop(columns=[target])
        y = df_clean[target]
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=args.test_size, random_state=args.random_state, stratify=y)
        train_df = pd.concat([X_train, y_train.reset_index(drop=True)], axis=1)
        val_df = pd.concat([X_val, y_val.reset_index(drop=True)], axis=1)
    else:
        train_df, val_df = train_test_split(df_clean, test_size=args.test_size, random_state=args.random_state)

    train_path = os.path.join(args.output_dir, 'train.csv')
    val_path = os.path.join(args.output_dir, 'val.csv')
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    print(f"Saved train -> {train_path}, val -> {val_path}")

    if args.upload:
        if not args.s3_bucket:
            raise SystemExit('s3-bucket is required when --upload is set')
        s3 = boto3.client('s3')
        upload_file(s3, train_path, args.s3_bucket, 'processed/train.csv')
        upload_file(s3, val_path, args.s3_bucket, 'processed/val.csv')


if __name__ == '__main__':
    main()
