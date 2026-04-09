"""
Comprehensive accuracy report generation module
"""

import json
import pandas as pd
from datetime import datetime


def generate_accuracy_report(results, y_test, models_info):
    """
    Generate a comprehensive accuracy report and save to file
    
    Args:
        results: Dictionary of model evaluation results
        y_test: Test target values
        models_info: Dictionary with additional model information
    """
    print("\n" + "=" * 80)
    print("GENERATING COMPREHENSIVE ACCURACY REPORT")
    print("=" * 80)
    
    # Create report data
    report = {
        'report_generated': datetime.now().isoformat(),
        'dataset_info': {
            'total_samples': models_info['total_samples'],
            'train_samples': models_info['train_samples'],
            'test_samples': len(y_test),
            'positive_class_percentage': models_info['positive_class_pct'],
            'features': models_info['features']
        },
        'training_info': {
            'smote_applied': True,
            'smote_strategy': '50/50 balance',
            'test_set_untouched': True,
            'random_state': 42
        },
        'model_results': {}
    }
    
    # Add results for each model
    for model_name, metrics in results.items():
        report['model_results'][model_name] = {
            'precision_class_0': float(metrics.get('Precision(0)', 0)),
            'recall_class_0': float(metrics.get('Recall(0)', 0)),
            'f1_class_0': float(metrics.get('F1(0)', 0)),
            'precision_class_1': float(metrics['Precision(1)']),
            'recall_class_1': float(metrics['Recall(1)']),
            'f1_class_1': float(metrics['F1(1)']),
            'accuracy': float(metrics['Accuracy']),
            'roc_auc': float(metrics['ROC-AUC']),
            'confusion_matrix': {
                'true_negatives': int(metrics['TN']),
                'false_positives': int(metrics['FP']),
                'false_negatives': int(metrics['FN']),
                'true_positives': int(metrics['TP'])
            }
        }
    
    # Save to JSON
    with open('accuracy_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    print("✓ Saved: accuracy_report.json")
    
    # Generate human-readable text report
    generate_text_report(report)
    
    return report


def generate_text_report(report):
    """
    Generate human-readable text report
    
    Args:
        report: Dictionary containing report data
    """
    lines = []
    lines.append("=" * 80)
    lines.append("COMPREHENSIVE ACCURACY REPORT")
    lines.append("=" * 80)
    lines.append(f"\nReport Generated: {report['report_generated']}")
    
    # Dataset info
    lines.append("\n" + "-" * 80)
    lines.append("DATASET INFORMATION")
    lines.append("-" * 80)
    ds = report['dataset_info']
    lines.append(f"Total Samples:              {ds['total_samples']}")
    lines.append(f"Training Samples:           {ds['train_samples']}")
    lines.append(f"Test Samples:               {ds['test_samples']}")
    lines.append(f"Positive Class %:           {ds['positive_class_percentage']:.2f}%")
    lines.append(f"Number of Features:         {len(ds['features'])}")
    
    # Training info
    lines.append("\n" + "-" * 80)
    lines.append("TRAINING CONFIGURATION")
    lines.append("-" * 80)
    ti = report['training_info']
    lines.append(f"SMOTE Applied:              {ti['smote_applied']}")
    lines.append(f"SMOTE Strategy:             {ti['smote_strategy']}")
    lines.append(f"Test Set Untouched:         {ti['test_set_untouched']}")
    lines.append(f"Random State:               {ti['random_state']}")
    
    # Model results
    lines.append("\n" + "-" * 80)
    lines.append("MODEL PERFORMANCE COMPARISON")
    lines.append("-" * 80)
    
    # Create comparison table
    table_data = []
    for model_name, metrics in report['model_results'].items():
        table_data.append({
            'Model': model_name,
            'Accuracy': f"{metrics['accuracy']:.4f}",
            'Precision(1)': f"{metrics['precision_class_1']:.4f}",
            'Recall(1)': f"{metrics['recall_class_1']:.4f}",
            'F1(1)': f"{metrics['f1_class_1']:.4f}",
            'ROC-AUC': f"{metrics['roc_auc']:.4f}"
        })
    
    df = pd.DataFrame(table_data)
    lines.append("\n" + df.to_string(index=False))
    
    # Detailed metrics per model
    lines.append("\n" + "-" * 80)
    lines.append("DETAILED METRICS BY MODEL")
    lines.append("-" * 80)
    
    for model_name, metrics in report['model_results'].items():
        lines.append(f"\n{model_name}:")
        lines.append(f"  Overall Accuracy:         {metrics['accuracy']:.4f}")
        lines.append(f"  ROC-AUC Score:            {metrics['roc_auc']:.4f}")
        lines.append(f"\n  Class 0 (No Violation):")
        lines.append(f"    Precision:              {metrics['precision_class_0']:.4f}")
        lines.append(f"    Recall:                 {metrics['recall_class_0']:.4f}")
        lines.append(f"    F1-Score:               {metrics['f1_class_0']:.4f}")
        lines.append(f"\n  Class 1 (Violation):")
        lines.append(f"    Precision:              {metrics['precision_class_1']:.4f}")
        lines.append(f"    Recall:                 {metrics['recall_class_1']:.4f}")
        lines.append(f"    F1-Score:               {metrics['f1_class_1']:.4f}")
        
        cm = metrics['confusion_matrix']
        lines.append(f"\n  Confusion Matrix:")
        lines.append(f"    True Negatives:         {cm['true_negatives']}")
        lines.append(f"    False Positives:        {cm['false_positives']}")
        lines.append(f"    False Negatives:        {cm['false_negatives']}")
        lines.append(f"    True Positives:         {cm['true_positives']}")
        
        # Calculate additional metrics
        total_violations = cm['true_positives'] + cm['false_negatives']
        missed_violations = cm['false_negatives']
        false_alarms = cm['false_positives']
        
        lines.append(f"\n  Violation Detection:")
        lines.append(f"    Total Violations:       {total_violations}")
        lines.append(f"    Detected:               {cm['true_positives']} ({cm['true_positives']/total_violations*100:.1f}%)")
        lines.append(f"    Missed:                 {missed_violations} ({missed_violations/total_violations*100:.1f}%)")
        lines.append(f"    False Alarms:           {false_alarms}")
    
    # Recommendations
    lines.append("\n" + "-" * 80)
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 80)
    
    # Find best model for each metric
    best_accuracy = max(report['model_results'].items(), key=lambda x: x[1]['accuracy'])
    best_recall = max(report['model_results'].items(), key=lambda x: x[1]['recall_class_1'])
    best_roc_auc = max(report['model_results'].items(), key=lambda x: x[1]['roc_auc'])
    
    lines.append(f"\nBest Overall Accuracy:      {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.4f})")
    lines.append(f"Best Recall (Violations):   {best_recall[0]} ({best_recall[1]['recall_class_1']:.4f})")
    lines.append(f"Best ROC-AUC:               {best_roc_auc[0]} ({best_roc_auc[1]['roc_auc']:.4f})")
    
    lines.append("\nFor production deployment:")
    lines.append(f"  • Use {best_recall[0]} if minimizing missed violations is critical")
    lines.append(f"  • Use {best_roc_auc[0]} for best overall discrimination capability")
    lines.append(f"  • Use {best_accuracy[0]} for highest overall accuracy")
    
    lines.append("\n" + "=" * 80)
    
    # Save text report
    report_text = "\n".join(lines)
    with open('accuracy_report.txt', 'w') as f:
        f.write(report_text)
    
    print("✓ Saved: accuracy_report.txt")
    
    # Print to console
    print("\n" + report_text)
