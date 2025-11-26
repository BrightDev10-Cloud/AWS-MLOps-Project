"""Unit tests for preprocessing module."""

import pytest
import pandas as pd
import numpy as np
from preprocess_telco import clean_telco


class TestCleanTelco:
    """Tests for telco data cleaning."""
    
    def test_removes_customer_id(self):
        """Test that customerID column is removed."""
        df = pd.DataFrame({
            'customerID': ['1', '2', '3'],
            'tenure': [1, 2, 3],
            'Churn': ['Yes', 'No', 'Yes']
        })
        result = clean_telco(df)
        assert 'customerID' not in result.columns
    
    def test_converts_total_charges_to_numeric(self):
        """Test that TotalCharges is converted to numeric."""
        df = pd.DataFrame({
            'TotalCharges': ['100.5', '  ', '300.75'],
            'tenure': [1, 2, 3],
            'Churn': ['Yes', 'No', 'Yes']
        })
        result = clean_telco(df)
        assert result['TotalCharges'].dtype in ['float64', 'int64']
        assert not result['TotalCharges'].isna().any()
    
    def test_binary_mapping_yes_no(self):
        """Test that Yes/No columns are converted to 1/0."""
        df = pd.DataFrame({
            'Partner': ['Yes', 'No', 'Yes'],
            'Dependents': ['No', 'Yes', 'No'],
            'Churn': ['Yes', 'No', 'Yes']
        })
        result = clean_telco(df)
        assert set(result['Partner'].unique()) <= {0, 1}
        assert set(result['Dependents'].unique()) <= {0, 1}
    
    def test_churn_target_mapping(self):
        """Test that Churn target is mapped to 0/1."""
        df = pd.DataFrame({
            'tenure': [1, 2, 3],
            'Churn': ['Yes', 'No', 'Yes']
        })
        result = clean_telco(df)
        assert set(result['Churn'].unique()) <= {0, 1}
        assert result['Churn'].tolist() == [1, 0, 1]
    
    def test_one_hot_encoding_categorical(self):
        """Test that categorical columns are one-hot encoded."""
        df = pd.DataFrame({
            'InternetService': ['DSL', 'Fiber optic', 'No'],
            'Contract': ['Month-to-month', 'One year', 'Two year'],
            'Churn': ['Yes', 'No', 'Yes']
        })
        result = clean_telco(df)
        # Original categorical columns should be encoded
        assert 'InternetService' not in result.columns
        assert 'Contract' not in result.columns
        # One-hot encoded columns should exist (with drop_first=True)
        encoded_cols = [col for col in result.columns if 'InternetService_' in col or 'Contract_' in col]
        assert len(encoded_cols) > 0
    
    def test_handles_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        result = clean_telco(df)
        assert len(result) == 0
    
    def test_fills_missing_numeric_values(self):
        """Test that missing TotalCharges values are filled with median."""
        df = pd.DataFrame({
            'tenure': [1, 2, 3, 4],
            'MonthlyCharges': [50.0, 60.0, 70.0, 80.0],
            'TotalCharges': ['50.0', '', '210.0', '320.0'],  # Empty string will become NaN
            'Churn': ['Yes', 'No', 'Yes', 'No']
        })
        result = clean_telco(df)
        # TotalCharges should have no NaN after cleaning
        assert not result['TotalCharges'].isna().any()


class TestPreprocessingIntegration:
    """Integration tests for preprocessing pipeline."""
    
    def test_full_preprocessing_pipeline(self):
        """Test complete preprocessing with realistic data."""
        # Create sample data similar to Telco dataset
        df = pd.DataFrame({
            'customerID': ['C1', 'C2', 'C3'],
            'gender': ['Male', 'Female', 'Male'],
            'SeniorCitizen': [0, 1, 0],
            'Partner': ['Yes', 'No', 'Yes'],
            'Dependents': ['No', 'No', 'Yes'],
            'tenure': [1, 34, 2],
            'PhoneService': ['Yes', 'Yes', 'No'],
            'InternetService': ['DSL', 'Fiber optic', 'No'],
            'Contract': ['Month-to-month', 'One year', 'Month-to-month'],
            'MonthlyCharges': [29.85, 56.95, 53.85],
            'TotalCharges': ['29.85', '1889.50', '108.15'],
            'Churn': ['No', 'No', 'Yes']
        })
        
        result = clean_telco(df)
        
        # Verify structure
        assert 'customerID' not in result.columns
        assert 'Churn' in result.columns
        assert len(result) == 3
        
        # Verify data types
        assert result['Churn'].dtype in ['int64', 'float64']
        assert result['tenure'].dtype in ['int64', 'float64']
        assert result['MonthlyCharges'].dtype in ['float64', 'int64']
        
        # Verify no missing values
        assert not result.isna().any().any()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
