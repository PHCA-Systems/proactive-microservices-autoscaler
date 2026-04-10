#!/usr/bin/env python3
"""
Setup script to create model directories for ML inference services
Copies models from experiment_no_service to the expected structure
"""

import shutil
from pathlib import Path


def setup_model_directory(source_model: Path, target_dir: Path, model_name: str):
    """Setup a model directory with the expected structure."""
    print(f"\nSetting up {model_name}...")
    print(f"  Source: {source_model}")
    print(f"  Target: {target_dir}")
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy model file as model.joblib
    target_model = target_dir / "model.joblib"
    shutil.copy2(source_model, target_model)
    print(f"  ✓ Copied model to {target_model}")
    
    # Create a basic parameters.json with service mapping
    params_file = target_dir / "parameters.json"
    params_content = """{
    "service_mapping": {
        "catalogue": 0,
        "carts": 1,
        "front-end": 2,
        "orders": 3,
        "payment": 4,
        "shipping": 5,
        "user": 6
    }
}"""
    params_file.write_text(params_content)
    print(f"  ✓ Created {params_file}")
    
    # Create a basic metrics.json (placeholder)
    metrics_file = target_dir / "metrics.json"
    metrics_content = """{
    "Accuracy": "N/A",
    "Recall(1)": "N/A",
    "Precision(1)": "N/A"
}"""
    metrics_file.write_text(metrics_content)
    print(f"  ✓ Created {metrics_file}")
    
    print(f"  ✓ {model_name} setup complete")


def main():
    """Main setup function."""
    print("="*80)
    print("ML MODEL DIRECTORY SETUP")
    print("="*80)
    print("Creating model directories for docker-compose deployment")
    
    # Source models
    source_base = Path("kafka-structured/ML-Models/gke/experiment_no_service/models")
    
    # Target base directory
    target_base = Path("kafka-structured/ML-Models/models")
    
    models = [
        ("model_xgb_gke_mixed.joblib", "xgboost", "XGBoost"),
        ("model_rf_gke_mixed.joblib", "random_forest", "Random Forest"),
        ("model_lr_gke_mixed.joblib", "logistic_regression", "Logistic Regression")
    ]
    
    for source_file, target_dir_name, display_name in models:
        source_model = source_base / source_file
        target_dir = target_base / target_dir_name
        
        if not source_model.exists():
            print(f"\n❌ ERROR: Source model not found: {source_model}")
            continue
        
        setup_model_directory(source_model, target_dir, display_name)
    
    print("\n" + "="*80)
    print("SETUP COMPLETE")
    print("="*80)
    print(f"Model directories created in: {target_base}")
    print("\nYou can now run:")
    print("  docker-compose -f kafka-structured/docker-compose.ml.yml --profile production up")


if __name__ == "__main__":
    main()
