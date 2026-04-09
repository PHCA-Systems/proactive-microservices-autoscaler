"""
Main pipeline script for SLA violation prediction model training

This orchestrates the entire training pipeline:
1. Data preprocessing
2. Train/test split
3. SMOTE balancing (training set only)
4. Model training (XGBoost, Random Forest, Logistic Regression)
5. Model evaluation
6. Feature importance analysis
7. Model persistence with parameters
8. Comprehensive accuracy report
"""

import warnings
warnings.filterwarnings('ignore')

from preprocessing import (
    load_and_preprocess_data,
    split_features_target,
    create_train_test_split
)
from smote_balancing import apply_smote
from model_training import train_all_models
from model_evaluation import evaluate_all_models, print_summary_table
from feature_importance import analyze_feature_importance
from model_persistence import save_models
from accuracy_report import generate_accuracy_report


def main():
    """Main pipeline execution"""
    
    print("\n" + "=" * 80)
    print("SLA VIOLATION PREDICTION - MODEL TRAINING PIPELINE")
    print("=" * 80)
    
    # Step 1: Preprocessing
    df = load_and_preprocess_data()
    X, y = split_features_target(df)
    
    # Step 2: Train/test split
    X_train, X_test, y_train, y_test = create_train_test_split(X, y)
    
    # Step 3: SMOTE balancing (training only)
    X_train_smote, y_train_smote, scale_pos_weight = apply_smote(X_train, y_train)
    
    # Step 4: Train models
    models = train_all_models(X_train_smote, y_train_smote, scale_pos_weight)
    
    # Step 5: Evaluate models
    results = evaluate_all_models(models, X_test, y_test)
    
    # Step 6: Feature importance
    analyze_feature_importance(models, X.columns.tolist())
    
    # Step 7: Save models with parameters and metrics
    save_models(models, results, scale_pos_weight)
    
    # Step 8: Summary
    print_summary_table(results)
    
    # Step 9: Generate comprehensive accuracy report
    models_info = {
        'total_samples': len(df),
        'train_samples': len(X_train_smote),
        'positive_class_pct': (y.sum() / len(y)) * 100,
        'features': X.columns.tolist()
    }
    generate_accuracy_report(results, y_test, models_info)
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
