"""
Example inference script showing how to load and use trained models

This demonstrates how to:
1. Load a saved model from the models directory
2. Load the parameters and service mapping
3. Preprocess new data for inference
4. Make predictions
"""

import joblib
import json
import pandas as pd
import numpy as np


def load_model_with_config(model_name):
    """
    Load a trained model with its configuration
    
    Args:
        model_name: One of 'xgboost', 'random_forest', 'logistic_regression'
        
    Returns:
        tuple: (model, parameters, metrics)
    """
    base_path = f'models/{model_name}'
    
    # Load model
    model = joblib.load(f'{base_path}/model.joblib')
    
    # Load parameters
    with open(f'{base_path}/parameters.json', 'r') as f:
        parameters = json.load(f)
    
    # Load metrics
    with open(f'{base_path}/metrics.json', 'r') as f:
        metrics = json.load(f)
    
    return model, parameters, metrics


def preprocess_for_inference(data, service_mapping):
    """
    Preprocess data for inference (same as training preprocessing)
    
    Args:
        data: Dictionary or DataFrame with raw features
        service_mapping: Service name to integer mapping
        
    Returns:
        pd.DataFrame: Preprocessed features ready for prediction
    """
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    else:
        df = data.copy()
    
    # Drop timestamp if present
    if 'timestamp' in df.columns:
        df = df.drop('timestamp', axis=1)
    
    # Encode service
    if 'service' in df.columns:
        df['service'] = df['service'].map(service_mapping)
    
    # Handle NaN and inf
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(0)
    
    # Remove target if present
    if 'sla_violated' in df.columns:
        df = df.drop('sla_violated', axis=1)
    
    return df


def predict_sla_violation(model, data, service_mapping):
    """
    Predict SLA violation for new data
    
    Args:
        model: Trained model
        data: Raw input data
        service_mapping: Service name to integer mapping
        
    Returns:
        tuple: (prediction, probability)
    """
    # Preprocess
    X = preprocess_for_inference(data, service_mapping)
    
    # Predict
    prediction = model.predict(X)[0]
    probability = model.predict_proba(X)[0]
    
    return prediction, probability


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("MODEL INFERENCE EXAMPLE")
    print("=" * 80)
    
    # Load XGBoost model (you can change to 'random_forest' or 'logistic_regression')
    model_name = 'xgboost'
    print(f"\nLoading {model_name} model...")
    model, params, metrics = load_model_with_config(model_name)
    
    print(f"✓ Model loaded successfully")
    print(f"  Accuracy: {metrics['Accuracy']:.4f}")
    print(f"  Recall (violations): {metrics['Recall(1)']:.4f}")
    print(f"  ROC-AUC: {metrics['ROC-AUC']:.4f}")
    
    # Example 1: Single prediction with dictionary
    print("\n" + "-" * 80)
    print("EXAMPLE 1: Single Prediction")
    print("-" * 80)
    
    sample_data = {
        'service': 'orders',
        'request_rate_rps': 150.5,
        'error_rate_pct': 2.3,
        'p50_latency_ms': 45.2,
        'p95_latency_ms': 120.5,
        'p99_latency_ms': 180.3,
        'cpu_usage_pct': 75.2,
        'memory_usage_mb': 512.8,
        'delta_rps': 25.3,
        'delta_p95_latency_ms': 15.2,
        'delta_cpu_usage_pct': 10.5
    }
    
    prediction, probability = predict_sla_violation(
        model, sample_data, params['service_mapping']
    )
    
    print(f"\nInput: {sample_data['service']} service")
    print(f"  Request Rate: {sample_data['request_rate_rps']} RPS")
    print(f"  CPU Usage: {sample_data['cpu_usage_pct']}%")
    print(f"  P95 Latency: {sample_data['p95_latency_ms']} ms")
    
    print(f"\nPrediction: {'SLA VIOLATION' if prediction == 1 else 'NO VIOLATION'}")
    print(f"Probability of violation: {probability[1]:.2%}")
    print(f"Confidence: {max(probability):.2%}")
    
    # Example 2: Batch prediction from CSV
    print("\n" + "-" * 80)
    print("EXAMPLE 2: Batch Prediction from CSV")
    print("-" * 80)
    
    # Load test data
    df = pd.read_csv('mixed_4hour_metrics.csv')
    sample_batch = df.head(10)
    
    # Preprocess
    X_batch = preprocess_for_inference(sample_batch, params['service_mapping'])
    
    # Predict
    predictions = model.predict(X_batch)
    probabilities = model.predict_proba(X_batch)
    
    # Show results
    results = pd.DataFrame({
        'service': sample_batch['service'].values,
        'cpu_usage': sample_batch['cpu_usage_pct'].values,
        'p95_latency': sample_batch['p95_latency_ms'].values,
        'predicted': predictions,
        'violation_prob': probabilities[:, 1],
        'actual': sample_batch['sla_violated'].values if 'sla_violated' in sample_batch.columns else None
    })
    
    print("\nBatch Prediction Results:")
    print(results.to_string(index=False))
    
    if 'sla_violated' in sample_batch.columns:
        accuracy = (predictions == sample_batch['sla_violated'].values).mean()
        print(f"\nBatch Accuracy: {accuracy:.2%}")
    
    print("\n" + "=" * 80)
    print("INFERENCE COMPLETE")
    print("=" * 80)
    
    print("\nTo use a different model, change the model_name variable to:")
    print("  - 'xgboost' (best overall accuracy)")
    print("  - 'random_forest' (best ROC-AUC)")
    print("  - 'logistic_regression' (best recall for violations)")
