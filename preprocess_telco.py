"""Preprocess Telco Customer Churn dataset.

Reads raw CSV, cleans dtypes, encodes categoricals, splits into train/validation,
saves CSVs locally and optionally uploads to s3://<bucket>/processed/.

Usage examples:
  python preprocess_telco.py --input-csv /path/WA_Fn-UseC_-Telco-Customer-Churn.csv --output-dir ./processed
  python preprocess_telco.py --input-csv /path/WA_Fn-UseC_-Telco-Customer-Churn.csv --s3-bucket my-bucket --upload
"""

import argparse
import os
import sys
import boto3
import pandas as pd
from sklearn.model_selection import train_test_split


def clean_telco(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the Telco dataset.
    
    Args:
        df: Raw dataframe from CSV
        
    Returns:
        Cleaned dataframe with proper dtypes
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Drop identifier
    if 'customerID' in df.columns:
        df = df.drop(columns=['customerID'])

    # Strip whitespace from all string columns
    obj_cols = df.select_dtypes(include=['object']).columns
    for c in obj_cols:
        df[c] = df[c].str.strip()

    # Convert TotalCharges to numeric (some rows are empty strings)
    if 'TotalCharges' in df.columns:
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
        # Fill TotalCharges NaN with median
        if df['TotalCharges'].isna().any():
            df['TotalCharges'] = df['TotalCharges'].fillna(df['TotalCharges'].median())

    # Handle Churn FIRST - convert Yes/No to 1/0
    if 'Churn' in df.columns:
        df['Churn'] = df['Churn'].map({'Yes': 1, 'No': 0})
    
    # Encode all other Yes/No columns as 1/0
    binary_cols = ['Partner', 'Dependents', 'PhoneService', 'PaperlessBilling']
    for col in binary_cols:
        if col in df.columns:
            df[col] = df[col].map({'Yes': 1, 'No': 0})
    
    # Handle columns with "No internet service" / "No phone service" values
    # These should map: Yes->1, No->0, "No service"->0
    service_cols = {
        'MultipleLines': {'Yes': 1, 'No': 0, 'No phone service': 0},
        'OnlineSecurity': {'Yes': 1, 'No': 0, 'No internet service': 0},
        'OnlineBackup': {'Yes': 1, 'No': 0, 'No internet service': 0},
        'DeviceProtection': {'Yes': 1, 'No': 0, 'No internet service': 0},
        'TechSupport': {'Yes': 1, 'No': 0, 'No internet service': 0},
        'StreamingTV': {'Yes': 1, 'No': 0, 'No internet service': 0},
        'StreamingMovies': {'Yes': 1, 'No': 0, 'No internet service': 0}
    }
    
    for col, mapping in service_cols.items():
        if col in df.columns:
            df[col] = df[col].map(mapping)
    
    # One-hot encode remaining categorical columns
    categorical_cols = ['gender', 'InternetService', 'Contract', 'PaymentMethod']
    existing_categ = [c for c in categorical_cols if c in df.columns]
    
    if existing_categ:
        df = pd.get_dummies(df, columns=existing_categ, drop_first=True)
    
    # Drop any rows with NaN in Churn (target variable)
    if 'Churn' in df.columns:
        before = len(df)
        df = df.dropna(subset=['Churn'])
        after = len(df)
        if before != after:
            print(f"Dropped {before - after} rows with missing Churn values")
    
    return df


def upload_file(s3_client, local_path, bucket, key):
    """Upload file to S3 with error handling."""
    try:
        s3_client.upload_file(local_path, bucket, key)
        print(f"✓ Uploaded {local_path} to s3://{bucket}/{key}")
    except Exception as e:
        print(f"✗ Failed to upload {local_path} to s3://{bucket}/{key}: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description='Preprocess Telco Churn CSV and optionally upload to S3')
    parser.add_argument('--input-csv', required=True, help='Path to raw Telco CSV')
    parser.add_argument('--output-dir', default='processed', help='Local output directory for processed CSVs')
    parser.add_argument('--test-size', type=float, default=0.2, help='Validation fraction')
    parser.add_argument('--random-state', type=int, default=42)
    parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket to upload processed CSVs (optional)')
    parser.add_argument('--upload', action='store_true', help='Upload processed CSVs to S3 if s3-bucket provided')
    args = parser.parse_args()

    try:
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
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
            )
            train_df = pd.concat([X_train.reset_index(drop=True), y_train.reset_index(drop=True)], axis=1)
            val_df = pd.concat([X_val.reset_index(drop=True), y_val.reset_index(drop=True)], axis=1)
        else:
            train_df, val_df = train_test_split(
                df_clean, test_size=args.test_size, random_state=args.random_state
            )

        train_path = os.path.join(args.output_dir, 'train.csv')
        val_path = os.path.join(args.output_dir, 'val.csv')
        train_df.to_csv(train_path, index=False)
        val_df.to_csv(val_path, index=False)
        print(f"✓ Saved train ({len(train_df)} rows) -> {train_path}")
        print(f"✓ Saved val ({len(val_df)} rows) -> {val_path}")

        if args.upload:
            if not args.s3_bucket:
                raise ValueError('--s3-bucket is required when --upload is set')
            s3 = boto3.client('s3')
            upload_file(s3, train_path, args.s3_bucket, 'processed/train.csv')
            upload_file(s3, val_path, args.s3_bucket, 'processed/val.csv')
            
        print("✓ Preprocessing completed successfully")
        return 0
        
    except Exception as e:
        print(f"✗ Preprocessing failed: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
