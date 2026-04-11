"""
Quick Overfitting Analysis - Examines test set results for overfitting indicators
"""

import os
import json
import numpy as np

OUTPUT_DIR = os.path.dirname(__file__)

print("=" * 80)
print("OVERFITTING ANALYSIS")
print("=" * 80)

# Load all results
results_files = {
    'Mixed Standard': 'results_mixed_standard.json',
    'Mixed One-Hot': 'results_mixed_onehot.json',
    'Separated Standard': 'results_separated_standard.json',
    'No Service (GKE Mixed)': 'experiment_no_service/results_no_service.json'
}

all_results = {}
for name, filepath in results_files.items():
    full_path = os.path.join(OUTPUT_DIR, filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            data = json.load(f)
            if 'GKE_Mixed' in data:
                all_results[name] = data['GKE_Mixed']
            else:
                all_results[name] = data
        print(f"✓ {name}")

print(f"\nLoaded {len(all_results)} experiments\n")

# ══════════════════════════════════════════════════════════════════════════════
# 1. SUSPICIOUS METRICS
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("SUSPICIOUS METRICS (Potential Overfitting Indicators)")
print("=" * 80)

suspicious = []

for exp_name, results in all_results.items():
    for model_name, metrics in results.items():
        issues = []
        
        # Perfect recall
        if metrics.get('recall_1', 0) >= 1.0:
            issues.append(f"Perfect recall (100%) - FN={metrics.get('fn', 0)}, TP={metrics.get('tp', 0)}")
        
        # Near-perfect recall
        elif metrics.get('recall_1', 0) >= 0.99:
            issues.append(f"Near-perfect recall ({metrics['recall_1']:.2%})")
        
        # Perfect precision
        if metrics.get('precision_1', 0) >= 1.0:
            issues.append(f"Perfect precision (100%) - FP={metrics.get('fp', 0)}, TP={metrics.get('tp', 0)}")
        
        # Near-perfect accuracy
        if metrics.get('accuracy', 0) >= 0.99:
            issues.append(f"Near-perfect accuracy ({metrics['accuracy']:.2%})")
        
        if issues:
            suspicious.append({
                'experiment': exp_name,
                'model': model_name,
                'issues': issues,
                'metrics': metrics
            })

if suspicious:
    for case in suspicious:
        print(f"\n⚠ {case['experiment']} - {case['model']}")
        for issue in case['issues']:
            print(f"   • {issue}")
        m = case['metrics']
        print(f"   Confusion: TP={m.get('tp')}, FP={m.get('fp')}, TN={m.get('tn')}, FN={m.get('fn')}")
else:
    print("\n✓ No suspicious metrics detected")

# ══════════════════════════════════════════════════════════════════════════════
# 2. PERFORMANCE VARIANCE
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("PERFORMANCE VARIANCE ACROSS EXPERIMENTS")
print("=" * 80)

models = ['XGBoost', 'RandomForest', 'LogisticRegression']

for model in models:
    print(f"\n{model}:")
    print("-" * 60)
    
    # Collect metrics across experiments
    f1_scores = []
    recall_scores = []
    precision_scores = []
    
    for exp_name, results in all_results.items():
        if model in results:
            f1_scores.append((exp_name, results[model].get('f1_1', 0)))
            recall_scores.append((exp_name, results[model].get('recall_1', 0)))
            precision_scores.append((exp_name, results[model].get('precision_1', 0)))
    
    # F1 variance
    if f1_scores:
        values = [v for _, v in f1_scores]
        print(f"  F1-Score: min={min(values):.4f}, max={max(values):.4f}, range={max(values)-min(values):.4f}")
        if max(values) - min(values) > 0.15:
            print(f"    ⚠ High variance (range > 0.15) - inconsistent across experiments")
    
    # Recall variance
    if recall_scores:
        values = [v for _, v in recall_scores]
        print(f"  Recall:   min={min(values):.4f}, max={max(values):.4f}, range={max(values)-min(values):.4f}")
        if max(values) - min(values) > 0.15:
            print(f"    ⚠ High variance (range > 0.15) - inconsistent across experiments")

# ══════════════════════════════════════════════════════════════════════════════
# 3. DETAILED ANALYSIS OF 100% RECALL CASE
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("DETAILED ANALYSIS: 100% RECALL CASE")
print("=" * 80)

for exp_name, results in all_results.items():
    for model_name, metrics in results.items():
        if metrics.get('recall_1', 0) >= 1.0:
            print(f"\n{exp_name} - {model_name}:")
            print(f"  Recall: {metrics['recall_1']:.4f} (100%)")
            print(f"  Precision: {metrics['precision_1']:.4f}")
            print(f"  F1-Score: {metrics['f1_1']:.4f}")
            print(f"  Accuracy: {metrics['accuracy']:.4f}")
            print(f"\n  Confusion Matrix:")
            print(f"    True Positives:  {metrics['tp']} (all violations caught)")
            print(f"    False Negatives: {metrics['fn']} (missed violations)")
            print(f"    False Positives: {metrics['fp']} (false alarms)")
            print(f"    True Negatives:  {metrics['tn']}")
            
            total_violations = metrics['tp'] + metrics['fn']
            total_predictions = metrics['tp'] + metrics['fp']
            
            print(f"\n  Interpretation:")
            print(f"    • Caught {metrics['tp']}/{total_violations} violations (100%)")
            print(f"    • Made {total_predictions} violation predictions")
            print(f"    • {metrics['fp']} were false alarms ({metrics['fp']/total_predictions*100:.1f}% of predictions)")
            
            if metrics['fp'] > metrics['tp'] * 0.5:
                print(f"    ⚠ High false positive rate - model may be too conservative")
            
            print(f"\n  Likely causes:")
            print(f"    • SMOTE over-sampling created many synthetic violation examples")
            print(f"    • class_weight='balanced' heavily penalizes missed violations")
            print(f"    • Model learned to be conservative (predict violation when uncertain)")
            
            print(f"\n  Is this overfitting?")
            print(f"    • Not necessarily - it's a deliberate trade-off")
            print(f"    • For autoscaling, false alarms are better than missed violations")
            print(f"    • However, too many false alarms waste resources")

# ══════════════════════════════════════════════════════════════════════════════
# 4. RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

print("\n1. CROSS-VALIDATION:")
print("   To properly assess overfitting, run k-fold cross-validation")
print("   Compare CV performance with single split performance")
print("   Large gap indicates overfitting to specific train/test split")

print("\n2. LEARNING CURVES:")
print("   Plot training vs validation performance as training size increases")
print("   Converging curves = good generalization")
print("   Diverging curves = overfitting")

print("\n3. FOR 100% RECALL MODELS:")
print("   • Acceptable if false positive rate is reasonable (<30%)")
print("   • Consider adjusting decision threshold if too many false alarms")
print("   • Monitor real-world performance - test set may not represent production")

print("\n4. GENERAL ADVICE:")
print("   • Random Forest with 95% accuracy looks most balanced")
print("   • XGBoost shows more consistent performance across experiments")
print("   • Logistic Regression's 100% recall is aggressive but may be useful")

print("\n" + "=" * 80)
