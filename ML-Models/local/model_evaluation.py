"""
Model evaluation module for testing and metrics
"""

import pandas as pd
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    roc_auc_score,
    precision_recall_fscore_support,
    accuracy_score
)


def evaluate_model(model, X_test, y_test, model_name):
    """
    Evaluate a single model on test set
    
    Args:
        model: Trained model
        X_test: Test features
        y_test: Test target
        model_name: Name of the model
        
    Returns:
        dict: Evaluation metrics
    """
    print(f"\n{'=' * 80}")
    print(f"MODEL: {model_name}")
    print(f"{'=' * 80}")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['No Violation', 'Violation']))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:")
    print(f"                 Predicted")
    print(f"                 0      1")
    print(f"Actual 0      {cm[0, 0]:4d}  {cm[0, 1]:4d}")
    print(f"       1      {cm[1, 0]:4d}  {cm[1, 1]:4d}")
    
    # ROC-AUC
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nROC-AUC Score: {roc_auc:.4f}")
    
    # Accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy Score: {accuracy:.4f}")
    
    # Extract metrics
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
    
    # Commentary on recall
    print(f"\n📊 Recall Analysis:")
    print(f"   Recall for class 1 (violations): {recall[1]:.3f}")
    print(f"   This means {recall[1]*100:.1f}% of actual violations were detected.")
    print(f"   False negatives (missed violations): {cm[1, 0]} out of {cm[1, 0] + cm[1, 1]}")
    
    return {
        'Precision(0)': precision[0],
        'Recall(0)': recall[0],
        'F1(0)': f1[0],
        'Precision(1)': precision[1],
        'Recall(1)': recall[1],
        'F1(1)': f1[1],
        'Accuracy': accuracy,
        'ROC-AUC': roc_auc,
        'TN': cm[0, 0],
        'FP': cm[0, 1],
        'FN': cm[1, 0],
        'TP': cm[1, 1]
    }


def evaluate_all_models(models, X_test, y_test):
    """
    Evaluate all models on test set
    
    Args:
        models: Dictionary of trained models
        X_test: Test features
        y_test: Test target
        
    Returns:
        dict: Results for all models
    """
    print("\n" + "=" * 80)
    print("MODEL EVALUATION ON TEST SET")
    print("=" * 80)
    
    results = {}
    for name, model in models.items():
        results[name] = evaluate_model(model, X_test, y_test, name)
    
    return results


def print_summary_table(results):
    """
    Print final summary comparison table
    
    Args:
        results: Dictionary of model results
    """
    print("\n" + "=" * 80)
    print("FINAL SUMMARY: MODEL COMPARISON")
    print("=" * 80)
    
    summary_df = pd.DataFrame(results).T
    summary_df = summary_df[['Precision(1)', 'Recall(1)', 'F1(1)', 'ROC-AUC']]
    
    print("\n" + summary_df.to_string())
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print("""
✓ All models trained on SMOTE-balanced training data (50/50 class distribution)
✓ Test set kept completely untouched - no SMOTE applied
  → This ensures unbiased performance estimates for thesis validity
  → Applying SMOTE to test data would leak information and inflate metrics artificially

✓ Recall for class 1 (SLA violations) is the priority metric
  → False negatives (missed violations) are more costly than false positives
  → A false alarm can be investigated; a missed violation impacts customers

✓ Models saved and ready for deployment in ML inference services
""")
