#!/usr/bin/env python3
"""
Test script to verify ML inference service model loading
Simulates what happens when the service starts
"""

import sys
import os
from pathlib import Path

# Add services directory to path
sys.path.insert(0, str(Path("kafka-structured/services/ml-inference")))

from model_loader import ModelLoader


def test_inference_service(model_path: str, model_name: str):
    """Test loading a model as the inference service would."""
    print(f"\n{'='*80}")
    print(f"Testing ML Inference Service: {model_name.upper()}")
    print(f"{'='*80}")
    print(f"Model Path: {model_path}")
    print(f"{'='*80}")
    
    # Simulate service startup
    print("\n[INFO] Loading model...")
    loader = ModelLoader(model_path)
    
    try:
        model, parameters, metrics = loader.load()
        print(f"[INFO] ✓ Model loaded successfully")
        print(f"[INFO] Model type: {type(model).__name__}")
        
        # Get service mapping
        service_mapping = loader.get_service_mapping()
        print(f"[INFO] Service mapping: {service_mapping}")
        
        # Display metrics if available
        if metrics:
            print(f"\n[INFO] Model Metrics:")
            for key, value in metrics.items():
                print(f"       {key}: {value}")
        
        print(f"\n✓ {model_name} inference service simulation PASSED")
        return True
        
    except Exception as e:
        print(f"[ERROR] ❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sample_inference(model_path: str, model_name: str):
    """Test running inference with a sample feature vector."""
    print(f"\n{'='*80}")
    print(f"Testing Sample Inference: {model_name.upper()}")
    print(f"{'='*80}")
    
    try:
        # Load model
        loader = ModelLoader(model_path)
        model, parameters, metrics = loader.load()
        service_mapping = loader.get_service_mapping()
        
        # Create a sample feature vector (10 features based on model)
        # Features: request_rate, error_rate, p50, p95, p99, cpu, memory, 
        #           delta_rps, delta_p95, delta_cpu
        sample_features = [
            100.0,   # request_rate_rps
            0.5,     # error_rate_pct
            15.0,    # p50_latency_ms
            35.0,    # p95_latency_ms (near SLO threshold of 36ms)
            50.0,    # p99_latency_ms
            60.0,    # cpu_usage_pct
            512.0,   # memory_usage_mb
            10.0,    # delta_rps (increasing)
            5.0,     # delta_p95_latency_ms (increasing)
            5.0      # delta_cpu_usage_pct (increasing)
        ]
        
        print(f"[INFO] Sample feature vector (10 features):")
        feature_names = [
            "request_rate_rps", "error_rate_pct", "p50_latency_ms",
            "p95_latency_ms", "p95_latency_ms", "cpu_usage_pct",
            "memory_usage_mb", "delta_rps", "delta_p95_latency_ms",
            "delta_cpu_usage_pct"
        ]
        for name, value in zip(feature_names, sample_features):
            print(f"       {name}: {value}")
        
        # Run prediction
        import numpy as np
        X = np.array([sample_features])
        
        prediction = model.predict(X)[0]
        
        # Get probability if available
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X)[0]
            prob_scale_up = probabilities[1]
            confidence = max(probabilities)
        else:
            prob_scale_up = 1.0 if prediction == 1 else 0.0
            confidence = 1.0
        
        action = "SCALE_UP" if prediction == 1 else "NO_OP"
        
        print(f"\n[INFO] Prediction Results:")
        print(f"       Decision: {action}")
        print(f"       Prediction: {prediction}")
        print(f"       Probability (SCALE_UP): {prob_scale_up:.4f}")
        print(f"       Confidence: {confidence:.4f}")
        
        print(f"\n✓ Sample inference test PASSED")
        return True
        
    except Exception as e:
        print(f"[ERROR] ❌ Inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("="*80)
    print("ML INFERENCE SERVICE VERIFICATION TEST")
    print("="*80)
    print("Simulating ML inference service startup and model loading")
    print("Testing with models from: ML-Models/models/")
    
    models = [
        ("kafka-structured/ML-Models/models/xgboost", "xgboost"),
        ("kafka-structured/ML-Models/models/random_forest", "random_forest"),
        ("kafka-structured/ML-Models/models/logistic_regression", "logistic_regression")
    ]
    
    results = []
    
    # Test model loading
    print("\n" + "="*80)
    print("PHASE 1: MODEL LOADING VERIFICATION")
    print("="*80)
    
    for model_path, model_name in models:
        success = test_inference_service(model_path, model_name)
        results.append((model_name, "loading", success))
    
    # Test sample inference
    print("\n" + "="*80)
    print("PHASE 2: SAMPLE INFERENCE VERIFICATION")
    print("="*80)
    
    for model_path, model_name in models:
        success = test_sample_inference(model_path, model_name)
        results.append((model_name, "inference", success))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    loading_results = [(name, success) for name, phase, success in results if phase == "loading"]
    inference_results = [(name, success) for name, phase, success in results if phase == "inference"]
    
    print("\nModel Loading:")
    for model_name, success in loading_results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"  {status}: {model_name}")
    
    print("\nSample Inference:")
    for model_name, success in inference_results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"  {status}: {model_name}")
    
    all_passed = all(success for _, _, success in results)
    
    if all_passed:
        print(f"\n✓ All tests PASSED!")
        print(f"\nVerification complete:")
        print(f"  ✓ Models load successfully")
        print(f"  ✓ Model type and file path are logged")
        print(f"  ✓ Inference works with sample feature vectors")
        print(f"\nRequirements 9.4 and 9.5 are satisfied:")
        print(f"  9.4: Model loading is logged with type and path")
        print(f"  9.5: Inference tested with sample feature vectors")
        return 0
    else:
        print(f"\n❌ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
