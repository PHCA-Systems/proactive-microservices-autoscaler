#!/usr/bin/env python3
"""
Test script to verify ML model loading
Tests loading of the three models from experiment_no_service
"""

import sys
import joblib
import json
from pathlib import Path


def test_model_loading(model_path: Path, model_name: str):
    """Test loading a single model."""
    print(f"\n{'='*80}")
    print(f"Testing: {model_name}")
    print(f"{'='*80}")
    print(f"Model path: {model_path}")
    
    # Check if model file exists
    model_file = model_path / "model.joblib"
    if not model_file.exists():
        print(f"❌ ERROR: Model file not found: {model_file}")
        return False
    
    print(f"✓ Model file exists: {model_file}")
    
    # Try to load the model
    try:
        model = joblib.load(str(model_file))
        print(f"✓ Model loaded successfully")
        print(f"  Model type: {type(model).__name__}")
    except Exception as e:
        print(f"❌ ERROR: Failed to load model: {e}")
        return False
    
    # Check for parameters file
    params_file = model_path / "parameters.json"
    if params_file.exists():
        try:
            with open(params_file, 'r') as f:
                parameters = json.load(f)
            print(f"✓ Parameters file loaded")
            if 'service_mapping' in parameters:
                print(f"  Service mapping: {parameters['service_mapping']}")
        except Exception as e:
            print(f"⚠ WARNING: Failed to load parameters: {e}")
    else:
        print(f"⚠ WARNING: Parameters file not found: {params_file}")
    
    # Check for metrics file
    metrics_file = model_path / "metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            print(f"✓ Metrics file loaded")
            print(f"  Accuracy: {metrics.get('Accuracy', 'N/A')}")
            print(f"  Recall(1): {metrics.get('Recall(1)', 'N/A')}")
            print(f"  Precision(1): {metrics.get('Precision(1)', 'N/A')}")
        except Exception as e:
            print(f"⚠ WARNING: Failed to load metrics: {e}")
    else:
        print(f"⚠ WARNING: Metrics file not found: {metrics_file}")
    
    print(f"✓ {model_name} verification PASSED")
    return True


def main():
    """Main test function."""
    print("="*80)
    print("ML MODEL LOADING VERIFICATION TEST")
    print("="*80)
    print("Testing models from: ML-Models/gke/experiment_no_service/models/")
    print("These are the gke_mixed versions (without service feature)")
    
    base_path = Path("kafka-structured/ML-Models/gke/experiment_no_service/models")
    
    if not base_path.exists():
        print(f"\n❌ ERROR: Base model directory not found: {base_path}")
        sys.exit(1)
    
    print(f"✓ Base model directory exists: {base_path}")
    
    # Test each model
    models_to_test = [
        ("model_lr_gke_mixed.joblib", "Logistic Regression (LR)"),
        ("model_rf_gke_mixed.joblib", "Random Forest (RF)"),
        ("model_xgb_gke_mixed.joblib", "XGBoost (XGB)")
    ]
    
    results = []
    
    for model_file, model_name in models_to_test:
        # For this test, we'll load the joblib file directly
        # In production, the model_loader expects a directory with model.joblib inside
        model_path = base_path / model_file
        
        print(f"\n{'='*80}")
        print(f"Testing: {model_name}")
        print(f"{'='*80}")
        print(f"Model file: {model_path}")
        
        if not model_path.exists():
            print(f"❌ ERROR: Model file not found: {model_path}")
            results.append((model_name, False))
            continue
        
        print(f"✓ Model file exists")
        
        # Try to load the model
        try:
            model = joblib.load(str(model_path))
            print(f"✓ Model loaded successfully")
            print(f"  Model type: {type(model).__name__}")
            
            # Try to get model attributes
            if hasattr(model, 'n_features_in_'):
                print(f"  Number of features: {model.n_features_in_}")
            
            if hasattr(model, 'classes_'):
                print(f"  Classes: {model.classes_}")
            
            results.append((model_name, True))
            print(f"✓ {model_name} verification PASSED")
            
        except Exception as e:
            print(f"❌ ERROR: Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            results.append((model_name, False))
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    for model_name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {model_name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print(f"\n✓ All models loaded successfully!")
        print(f"\nNext steps:")
        print(f"1. Models are ready for deployment")
        print(f"2. Ensure docker-compose or K8s manifests mount these model files")
        print(f"3. Set MODEL_PATH environment variable to point to model directories")
        return 0
    else:
        print(f"\n❌ Some models failed to load")
        return 1


if __name__ == "__main__":
    sys.exit(main())
