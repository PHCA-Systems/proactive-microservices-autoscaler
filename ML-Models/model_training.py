"""
Model training module for all three classifiers
"""

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from config import XGB_PARAMS, RF_PARAMS, LR_PARAMS


def train_xgboost(X_train, y_train, scale_pos_weight):
    """
    Train XGBoost classifier
    
    Args:
        X_train: Training features
        y_train: Training target
        scale_pos_weight: Weight for positive class
        
    Returns:
        Trained XGBoost model
    """
    print("\nTraining XGBoost...")
    model = XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        **XGB_PARAMS
    )
    model.fit(X_train, y_train)
    print("✓ XGBoost trained")
    return model


def train_random_forest(X_train, y_train):
    """
    Train Random Forest classifier
    
    Args:
        X_train: Training features
        y_train: Training target
        
    Returns:
        Trained Random Forest model
    """
    print("\nTraining Random Forest...")
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train, y_train)
    print("✓ Random Forest trained")
    return model


def train_logistic_regression(X_train, y_train):
    """
    Train Logistic Regression with StandardScaler in a Pipeline
    
    Args:
        X_train: Training features
        y_train: Training target
        
    Returns:
        Trained Logistic Regression pipeline
    """
    print("\nTraining Logistic Regression (with StandardScaler)...")
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(**LR_PARAMS))
    ])
    model.fit(X_train, y_train)
    print("✓ Logistic Regression trained")
    return model


def train_all_models(X_train, y_train, scale_pos_weight):
    """
    Train all three models
    
    Args:
        X_train: Training features
        y_train: Training target
        scale_pos_weight: Weight for XGBoost positive class
        
    Returns:
        dict: Dictionary of trained models
    """
    print("\n" + "=" * 80)
    print("MODEL TRAINING")
    print("=" * 80)
    
    models = {
        'XGBoost': train_xgboost(X_train, y_train, scale_pos_weight),
        'Random Forest': train_random_forest(X_train, y_train),
        'Logistic Regression': train_logistic_regression(X_train, y_train)
    }
    
    return models
