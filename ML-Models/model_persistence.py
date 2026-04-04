"""
Model persistence module for saving trained models
"""

import os
import json
import joblib
from config import (
    MODEL_XGB_PATH, MODEL_RF_PATH, MODEL_LR_PATH,
    MODEL_DIR_XGB, MODEL_DIR_RF, MODEL_DIR_LR,
    PARAMS_XGB_PATH, PARAMS_RF_PATH, PARAMS_LR_PATH,
    METRICS_XGB_PATH, METRICS_RF_PATH, METRICS_LR_PATH,
    XGB_PARAMS, RF_PARAMS, LR_PARAMS, SERVICE_MAPPING
)


def create_model_directories():
    """Create directories for each model"""
    os.makedirs(MODEL_DIR_XGB, exist_ok=True)
    os.makedirs(MODEL_DIR_RF, exist_ok=True)
    os.makedirs(MODEL_DIR_LR, exist_ok=True)


def save_parameters(model_name, params, scale_pos_weight=None):
    """
    Save model parameters to JSON file
    
    Args:
        model_name: Name of the model
        params: Dictionary of parameters
        scale_pos_weight: Optional scale_pos_weight for XGBoost
    """
    if model_name == 'XGBoost':
        path = PARAMS_XGB_PATH
        params_to_save = params.copy()
        if scale_pos_weight:
            params_to_save['scale_pos_weight'] = scale_pos_weight
    elif model_name == 'Random Forest':
        path = PARAMS_RF_PATH
        params_to_save = params.copy()
    else:  # Logistic Regression
        path = PARAMS_LR_PATH
        params_to_save = params.copy()
    
    # Add service mapping for inference
    params_to_save['service_mapping'] = SERVICE_MAPPING
    
    with open(path, 'w') as f:
        json.dump(params_to_save, f, indent=2)
    
    print(f"✓ Saved parameters: {path}")


def save_metrics(model_name, metrics):
    """
    Save model metrics to JSON file
    
    Args:
        model_name: Name of the model
        metrics: Dictionary of metrics
    """
    if model_name == 'XGBoost':
        path = METRICS_XGB_PATH
    elif model_name == 'Random Forest':
        path = METRICS_RF_PATH
    else:  # Logistic Regression
        path = METRICS_LR_PATH
    
    # Convert numpy types to Python native types
    metrics_serializable = {}
    for key, value in metrics.items():
        if hasattr(value, 'item'):  # numpy scalar
            metrics_serializable[key] = value.item()
        else:
            metrics_serializable[key] = float(value) if isinstance(value, (int, float)) else value
    
    with open(path, 'w') as f:
        json.dump(metrics_serializable, f, indent=2)
    
    print(f"✓ Saved metrics: {path}")


def save_models(models, results, scale_pos_weight):
    """
    Save all trained models, parameters, and metrics to disk
    
    Args:
        models: Dictionary of trained models
        results: Dictionary of evaluation results
        scale_pos_weight: Scale weight for XGBoost
    """
    print("\n" + "=" * 80)
    print("SAVING TRAINED MODELS, PARAMETERS & METRICS")
    print("=" * 80)
    
    # Create directories
    create_model_directories()
    
    # Save XGBoost
    print("\nXGBoost:")
    joblib.dump(models['XGBoost'], MODEL_XGB_PATH)
    print(f"✓ Saved model: {MODEL_XGB_PATH}")
    save_parameters('XGBoost', XGB_PARAMS, scale_pos_weight)
    save_metrics('XGBoost', results['XGBoost'])
    
    # Save Random Forest
    print("\nRandom Forest:")
    joblib.dump(models['Random Forest'], MODEL_RF_PATH)
    print(f"✓ Saved model: {MODEL_RF_PATH}")
    save_parameters('Random Forest', RF_PARAMS)
    save_metrics('Random Forest', results['Random Forest'])
    
    # Save Logistic Regression
    print("\nLogistic Regression:")
    joblib.dump(models['Logistic Regression'], MODEL_LR_PATH)
    print(f"✓ Saved model: {MODEL_LR_PATH}")
    save_parameters('Logistic Regression', LR_PARAMS)
    save_metrics('Logistic Regression', results['Logistic Regression'])
