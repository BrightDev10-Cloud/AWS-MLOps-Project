"""Simple drift detection using statistical tests.

Compares reference (training) data with current (production) data
to detect distribution shifts using basic statistical methods.
"""

import argparse
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any


def calculate_drift_score(reference_data: pd.DataFrame, current_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate drift score using KS test for numeric columns.
    
    Args:
        reference_data: Training/baseline data
        current_data: Current production data
        
    Returns:
        Dictionary with drift detection results
    """
    drift_results = {}
    drifted_features = []
    
    # Get numeric columns only
    numeric_cols = reference_data.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if col in current_data.columns:
            # Kolmogorov-Smirnov test
            ks_stat, p_value = stats.ks_2samp(
                reference_data[col].dropna(),
                current_data[col].dropna()
            )
            
            drift_results[col] = {
                'ks_statistic': float(ks_stat),
                'p_value': float(p_value),
                'drifted': bool(p_value < 0.05)  # Convert to Python bool
            }
            
            if p_value < 0.05:
                drifted_features.append(col)
    
    # Calculate drift share
    drift_share = len(drifted_features) / len(numeric_cols) if len(numeric_cols) > 0 else 0
    
    return {
        'drift_detected': len(drifted_features) > 0,
        'drift_share': drift_share,
        'drifted_features': drifted_features,
        'total_features': len(numeric_cols),
        'feature_results': drift_results,
        'timestamp': pd.Timestamp.now().isoformat()
    }


def generate_html_report(results: Dict[str, Any], output_path: str):
    """Generate simple HTML report."""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Drift Detection Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
            .drift {{ color: red; }}
            .no-drift {{ color: green; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Data Drift Detection Report</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Drift Detected:</strong> <span class="{'drift' if results['drift_detected'] else 'no-drift'}">
                {'YES - Action Required' if results['drift_detected'] else 'NO - All Good'}
            </span></p>
            <p><strong>Drift Share:</strong> {results['drift_share']:.1%} ({len(results['drifted_features'])} / {results['total_features']} features)</p>
            <p><strong>Timestamp:</strong> {results['timestamp']}</p>
        </div>
        
        <h2>Feature-Level Results</h2>
        <table>
            <tr>
                <th>Feature</th>
                <th>KS Statistic</th>
                <th>P-Value</th>
                <th>Drift Status</th>
            </tr>
    """
    
    for feature, data in sorted(results['feature_results'].items()):
        status = "DRIFT" if data['drifted'] else "OK"
        status_class = "drift" if data['drifted'] else "no-drift"
        html += f"""
            <tr>
                <td>{feature}</td>
                <td>{data['ks_statistic']:.4f}</td>
                <td>{data['p_value']:.4f}</td>
                <td class="{status_class}"><strong>{status}</strong></td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Interpretation</h2>
        <p>
        This report uses the <strong>Kolmogorov-Smirnov test</strong> to compare distributions 
        between reference (training) data and current (production) data.
        </p>
        <ul>
            <li>P-value < 0.05 indicates significant drift</li>
            <li>KS statistic closer to 1 indicates larger distribution difference</li>
        </ul>
    </body>
    </html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✓ Drift report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Simple drift detection using statistical tests')
    parser.add_argument('--reference-csv', required=True, help='Path to reference/training CSV')
    parser.add_argument('--current-csv', required=True, help='Path to current production CSV')
    parser.add_argument('--output-html', default='drift_report.html', help='Output HTML report path')
    parser.add_argument('--output-json', default='drift_results.json', help='Output JSON results path')
    parser.add_argument('--threshold', type=float, default=0.3, help='Drift threshold (0-1)')
    args = parser.parse_args()
    
    try:
        # Load data
        print(f"Loading reference data from {args.reference_csv}...")
        reference_data = pd.read_csv(args.reference_csv)
        print(f"Loaded {len(reference_data)} reference samples")
        
        print(f"Loading current data from {args.current_csv}...")
        current_data = pd.read_csv(args.current_csv)
        print(f"Loaded {len(current_data)} current samples")
        
        # Remove target column if present
        for col in ['Churn', 'target']:
            if col in reference_data.columns:
                reference_data = reference_data.drop(columns=[col])
            if col in current_data.columns:
                current_data = current_data.drop(columns=[col])
        
        # Calculate drift
        print("Calculating drift scores...")
        results = calculate_drift_score(reference_data, current_data)
        
        # Generate HTML report
        generate_html_report(results, args.output_html)
        
        # Save JSON results
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Drift results saved to {args.output_json}")
        
        # Print summary
        print(f"\nDrift Detection Results:")
        print(f"  Drift detected: {results['drift_detected']}")
        print(f"  Drift share: {results['drift_share']:.2%}")
        print(f"  Threshold: {args.threshold:.2%}")
        print(f"  Exceeds threshold: {results['drift_share'] > args.threshold}")
        
        if results['drifted_features']:
            print(f"\n  Drifted features: {', '.join(results['drifted_features'])}")
        
        # Return non-zero if drift exceeds threshold
        return 1 if results['drift_share'] > args.threshold else 0
        
    except Exception as e:
        print(f"✗ Drift detection failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
