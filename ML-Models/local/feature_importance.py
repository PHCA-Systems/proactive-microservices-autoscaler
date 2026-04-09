"""
Feature importance analysis module
"""

import numpy as np
import matplotlib.pyplot as plt
from config import PLOT_DPI, PLOT_FIGSIZE


def plot_tree_feature_importance(model, feature_names, model_name, output_path):
    """
    Plot and save feature importance for tree-based models
    
    Args:
        model: Trained tree-based model (XGBoost or Random Forest)
        feature_names: List of feature names
        model_name: Name of the model for plot title
        output_path: Path to save the plot
    """
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    plt.figure(figsize=PLOT_FIGSIZE)
    plt.title(f'{model_name} Feature Importances', fontsize=14, fontweight='bold')
    plt.bar(range(len(importances)), importances[indices])
    plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=45, ha='right')
    plt.xlabel('Features')
    plt.ylabel('Importance')
    plt.tight_layout()
    plt.savefig(output_path, dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {output_path}")


def print_lr_coefficients(model, feature_names):
    """
    Print Logistic Regression coefficient magnitudes
    
    Args:
        model: Trained Logistic Regression pipeline
        feature_names: List of feature names
    """
    print("\nLogistic Regression Coefficient Magnitudes:")
    lr_coefs = model.named_steps['classifier'].coef_[0]
    lr_coef_abs = np.abs(lr_coefs)
    lr_indices = np.argsort(lr_coef_abs)[::-1]
    
    for idx in lr_indices:
        print(f"  {feature_names[idx]:25s}: {lr_coef_abs[idx]:8.4f} (raw: {lr_coefs[idx]:8.4f})")


def analyze_feature_importance(models, feature_names):
    """
    Analyze and visualize feature importance for all models
    
    Args:
        models: Dictionary of trained models
        feature_names: List of feature names
    """
    print("\n" + "=" * 80)
    print("FEATURE IMPORTANCE ANALYSIS")
    print("=" * 80)
    
    # XGBoost
    print("\nGenerating XGBoost feature importance plot...")
    plot_tree_feature_importance(
        models['XGBoost'], 
        feature_names, 
        'XGBoost', 
        'feature_importance_xgb.png'
    )
    
    # Random Forest
    print("\nGenerating Random Forest feature importance plot...")
    plot_tree_feature_importance(
        models['Random Forest'], 
        feature_names, 
        'Random Forest', 
        'feature_importance_rf.png'
    )
    
    # Logistic Regression
    print_lr_coefficients(models['Logistic Regression'], feature_names)
