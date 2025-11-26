"""drift_detection.py
Monitor data drift using Evidently AI.
Compares reference data (training data) against current production data
to detect distribution shifts.
"""

import argparse
import json
import sys
from pathlib import Path
import pandas as pd
import boto3
from evidently import Report
from evidently.presets import DataDriftPreset, DataSummaryPreset
# DatasetDriftMetric is not directly available in top-level metrics in this version, 
# but DataDriftPreset covers it.
from config import config


def download_from_s3(bucket: str, key: str, local_path: str, region: str = None):
    """Download file from S3."""
    s3 = boto3.client('s3', region_name=region) if region else boto3.client('s3')
    try:
        s3.download_file(bucket, key, local_path)
        print(f"✓ Downloaded s3://{bucket}/{key} to {local_path}")
    except Exception as e:
        print(f"✗ Failed to download from S3: {e}", file=sys.stderr)
        raise


def upload_to_s3(bucket: str, key: str, local_path: str, region: str = None):
    """Upload file to S3."""
    s3 = boto3.client('s3', region_name=region) if region else boto3.client('s3')
    try:
        s3.upload_file(local_path, bucket, key)
        print(f"✓ Uploaded {local_path} to s3://{bucket}/{key}")
    except Exception as e:
        print(f"✗ Failed to upload to S3: {e}", file=sys.stderr)
        raise


def generate_drift_report(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    output_path: str = "drift_report.html"
) -> dict:
    """Generate drift detection report using Evidently.
    
    Args:
        reference_data: Training/baseline data
        current_data: Current production data
        output_path: Path to save HTML report
        
    Returns:
        Dictionary with drift detection results
    """
    # Create drift report
    report = Report(metrics=[
        DataDriftPreset(),
        DataQualityPreset(),
        DatasetDriftMetric(),
    ])
    
    # Run the report
    report.run(reference_data=reference_data, current_data=current_data)
    
    # Save HTML report
    report.save_html(output_path)
    print(f"✓ Drift report saved to {output_path}")
    
    # Extract drift metrics
    report_dict = report.as_dict()
    
    # Get overall drift status
    drift_detected = report_dict['metrics'][2]['result']['dataset_drift']
    drift_share = report_dict['metrics'][2]['result']['drift_share']
    
    results = {
        'drift_detected': drift_detected,
        'drift_share': drift_share,
        'timestamp': pd.Timestamp.now().isoformat(),
    }
    
    return results


def check_drift_threshold(drift_share: float, threshold: float = 0.3) -> bool:
    """Check if drift exceeds threshold.
    
    Args:
        drift_share: Proportion of features with drift
        threshold: Maximum acceptable drift proportion
        
    Returns:
        True if drift exceeds threshold
    """
    return drift_share > threshold


def main():
    parser = argparse.ArgumentParser(description='Monitor data drift with Evidently AI')
    parser.add_argument('--reference-csv', required=True, help='Path to reference/training CSV')
    parser.add_argument('--current-csv', required=True, help='Path to current production CSV')
    parser.add_argument('--output-html', default='drift_report.html', help='Output HTML report path')
    parser.add_argument('--output-json', default='drift_results.json', help='Output JSON results path')
    parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket to upload report (optional)')
    parser.add_argument('--s3-key-prefix', default='monitoring/drift/', help='S3 key prefix for reports')
    parser.add_argument('--threshold', type=float, default=None, help='Drift threshold (default: from config)')
    parser.add_argument('--alert-sns', action='store_true', help='Send SNS alert if drift detected')
    args = parser.parse_args()
    
    try:
        # Load data
        print(f"Loading reference data from {args.reference_csv}...")
        reference_data = pd.read_csv(args.reference_csv)
        print(f"Loaded {len(reference_data)} reference samples")
        
        print(f"Loading current data from {args.current_csv}...")
        current_data = pd.read_csv(args.current_csv)
        print(f"Loaded {len(current_data)} current samples")
        
        # Remove target column if present (for drift detection on features only)
        for col in ['Churn', 'target']:
            if col in reference_data.columns:
                reference_data = reference_data.drop(columns=[col])
            if col in current_data.columns:
                current_data = current_data.drop(columns=[col])
        
        # Generate drift report
        print("Generating drift report...")
        results = generate_drift_report(reference_data, current_data, args.output_html)
        
        # Save results to JSON
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Drift results saved to {args.output_json}")
        
        # Check threshold
        threshold = args.threshold if args.threshold is not None else config.drift_threshold
        drift_exceeds_threshold = check_drift_threshold(results['drift_share'], threshold)
        
        print(f"\nDrift Detection Results:")
        print(f"  Drift detected: {results['drift_detected']}")
        print(f"  Drift share: {results['drift_share']:.2%}")
        print(f"  Threshold: {threshold:.2%}")
        print(f"  Exceeds threshold: {drift_exceeds_threshold}")
        
        # Upload to S3 if requested
        if args.s3_bucket:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            html_key = f"{args.s3_key_prefix}drift_report_{timestamp}.html"
            json_key = f"{args.s3_key_prefix}drift_results_{timestamp}.json"
            
            upload_to_s3(args.s3_bucket, html_key, args.output_html, region=config.aws_region)
            upload_to_s3(args.s3_bucket, json_key, args.output_json, region=config.aws_region)
        
        # Send SNS alert if drift exceeds threshold
        if args.alert_sns and drift_exceeds_threshold and config.sns_topic_arn:
            sns = boto3.client('sns', region_name=config.aws_region)
            message = f"""
Data Drift Alert - MLOps Pipeline

Drift Share: {results['drift_share']:.2%}
Threshold: {threshold:.2%}
Status: EXCEEDS THRESHOLD

Drift detected: {results['drift_detected']}
Timestamp: {results['timestamp']}

Please review the drift report and consider retraining the model.
            """
            
            sns.publish(
                TopicArn=config.sns_topic_arn,
                Subject='MLOps: Data Drift Detected',
                Message=message
            )
            print("✓ SNS alert sent")
        
        # Return non-zero if drift exceeds threshold
        return 1 if drift_exceeds_threshold else 0
        
    except Exception as e:
        print(f"✗ Drift detection failed: {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
