"""
Data preprocessing module for SLA violation prediction
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from config import SERVICE_MAPPING, DATA_PATH, TEST_SIZE, RANDOM_STATE


def load_and_preprocess_data():
    """
    Load CSV data and perform preprocessing steps:
    - Drop timestamp column
    - Label-encode service column with fixed mapping
    - Handle NaN and inf values
    
    Returns:
        pd.DataFrame: Preprocessed dataframe
    """
    print("=" * 80)
    print("DATA PREPROCESSING")
    print("=" * 80)
    
    # Load data
    df = pd.read_csv(DATA_PATH)
    print(f"\nLoaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Drop timestamp column
    df = df.drop('timestamp', axis=1)
    print("Dropped 'timestamp' column")
    
    # Label-encode service column with fixed mapping
    df['service'] = df['service'].map(SERVICE_MAPPING)
    print(f"Label-encoded 'service' column using fixed mapping")
    
    # Check for NaN and inf values
    nan_count = df.isnull().sum().sum()
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    print(f"\nNaN values found: {nan_count}")
    print(f"Inf values found: {inf_count}")
    
    # Fill NaN and inf with 0
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(0)
    print("Filled all NaN and inf values with 0")
    
    return df


def split_features_target(df):
    """
    Split dataframe into features (X) and target (y)
    
    Args:
        df: Preprocessed dataframe
        
    Returns:
        tuple: (X, y) features and target
    """
    X = df.drop('sla_violated', axis=1)
    y = df['sla_violated']
    
    print(f"\nFeatures shape: {X.shape}")
    print(f"Target shape: {y.shape}")
    print(f"Feature columns: {list(X.columns)}")
    
    return X, y


def create_train_test_split(X, y):
    """
    Create stratified train/test split
    
    Args:
        X: Features
        y: Target
        
    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    print("\n" + "=" * 80)
    print("TRAIN/TEST SPLIT")
    print("=" * 80)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    
    print(f"\nTrain set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    print(f"\nOriginal training set class distribution:")
    print(f"  Class 0 (no violation): {(y_train == 0).sum()} ({(y_train == 0).sum() / len(y_train) * 100:.1f}%)")
    print(f"  Class 1 (violation):    {(y_train == 1).sum()} ({(y_train == 1).sum() / len(y_train) * 100:.1f}%)")
    
    return X_train, X_test, y_train, y_test
