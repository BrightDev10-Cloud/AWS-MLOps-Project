"""Unit tests for model training."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import os
import json


class TestTrainingPipeline:
    """Tests for training pipeline."""
    
    def test_model_training_with_valid_data(self):
        """Test that model trains successfully with valid data."""
        from train_model import main
        import argparse
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample training data
            train_data = pd.DataFrame({
                'feature1': np.random.rand(100),
                'feature2': np.random.rand(100),
                'feature3': np.random.rand(100),
                'Churn': np.random.randint(0, 2, 100)
            })
            val_data = pd.DataFrame({
                'feature1': np.random.rand(20),
                'feature2': np.random.rand(20),
                'feature3': np.random.rand(20),
                'Churn': np.random.randint(0, 2, 20)
            })
            
            train_path = os.path.join(tmpdir, 'train.csv')
            val_path = os.path.join(tmpdir, 'val.csv')
            model_path = os.path.join(tmpdir, 'model.joblib')
            
            train_data.to_csv(train_path, index=False)
            val_data.to_csv(val_path, index=False)
            
            # Create arguments
            args = argparse.Namespace(
                train_csv=train_path,
                val_csv=val_path,
                output_model=model_path,
                metrics_path=None,
                n_estimators=10,
                package=False,
                tar_name='model.tar.gz',
                s3_bucket=None,
                aws_region=None
            )
            
            # Mock MLflow to avoid actual tracking
            with patch('train_model.mlflow'):
                result = main(args)
            
            # Verify model was created
            assert os.path.exists(model_path)
            assert result == 0
    
    def test_metrics_calculation(self):
        """Test that metrics are calculated correctly."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        y_true = [0, 1, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1]
        
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        assert 0 <= accuracy <= 1
        assert 0 <= precision <= 1
        assert 0 <= recall <= 1
        assert 0 <= f1 <= 1
        assert accuracy == 0.8  # 4 out of 5 correct
    
    def test_model_saves_metrics_json(self):
        """Test that metrics are saved to JSON file."""
        from train_model import main
        import argparse
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample data
            train_data = pd.DataFrame({
                'feature1': np.random.rand(50),
                'Churn': np.random.randint(0, 2, 50)
            })
            val_data = pd.DataFrame({
                'feature1': np.random.rand(10),
                'Churn': np.random.randint(0, 2, 10)
            })
            
            train_path = os.path.join(tmpdir, 'train.csv')
            val_path = os.path.join(tmpdir, 'val.csv')
            model_path = os.path.join(tmpdir, 'model.joblib')
            metrics_path = os.path.join(tmpdir, 'metrics.json')
            
            train_data.to_csv(train_path, index=False)
            val_data.to_csv(val_path, index=False)
            
            args = argparse.Namespace(
                train_csv=train_path,
                val_csv=val_path,
                output_model=model_path,
                metrics_path=metrics_path,
                n_estimators=5,
                package=False,
                tar_name='model.tar.gz',
                s3_bucket=None,
                aws_region=None
            )
            
            with patch('train_model.mlflow'):
                main(args)
            
            # Verify metrics file exists
            assert os.path.exists(metrics_path)
            
            # Verify metrics structure
            with open(metrics_path) as f:
                metrics = json.load(f)
            
            assert 'accuracy' in metrics
            assert 'precision' in metrics
            assert 'recall' in metrics
            assert 'f1' in metrics


class TestModelArtifacts:
    """Tests for model artifact creation."""
    
    def test_model_packaging(self):
        """Test that model can be packaged into tar.gz."""
        import tarfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy model file
            model_path = os.path.join(tmpdir, 'model.joblib')
            with open(model_path, 'w') as f:
                f.write('dummy model content')
            
            # Create tar.gz
            tar_path = os.path.join(tmpdir, 'model.tar.gz')
            with tarfile.open(tar_path, 'w:gz') as tar:
                tar.add(model_path, arcname='model.joblib')
            
            # Verify tar was created
            assert os.path.exists(tar_path)
            
            # Verify contents
            with tarfile.open(tar_path, 'r:gz') as tar:
                members = tar.getmembers()
                assert len(members) == 1
                assert members[0].name == 'model.joblib'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
