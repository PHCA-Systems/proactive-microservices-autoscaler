"""
Comprehensive Overfitting Analysis Across All Experiments

This script analyzes potential overfitting by:
1. Comparing train vs test performance (if available)
2. Analyzing performance variance across different datasets
3. Checking for suspiciously high metrics
4. Examining confusion matrix patterns
5. Cross-validation analysis
"""

import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import joblib
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(__file__)

print("=" * 80)
print("OVERFITTING ANALYSIS ACROSS ALL EXPERIMENTS")
print("=" * 80)

# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD ALL RESULTS
# ══════════════════════════════════════════════════════════════════════════════

results_files = {
    'Mixed Standard': 'results_mixed_standard.json',
    'Mixed One-Hot': 'results_mixed_onehot.json',
    'Separated Standard': 'results_separated_standard.json',
    'Separated Cross-Pattern': 'results_separated_cross_pattern.json',
    'No Service (GKE Mixed)': 'experiment_no_service/results_no_service.json'
}

all_results = {}
for name, filepath in results_files.items():
    full_path = os.path.join(OUTPUT_DIR, filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            data = json.load(f)
            # Handle nested structure
            if 'GKE_Mixed' in data:
                all_results[name] = data['GKE_Mixed']
            else:
                all_results[name] = data
        print(f"✓ Loaded: {name}")
    else:
        print(f"✗ Missing: {name}")

print(f"\nTotal experiments loaded: {len(all_results)}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. IDENTIFY SUSPICIOUS METRICS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("SUSPICIOUS METRICS DETECTION")
print("=" * 80)

suspicious_cases = []

for exp_name, results in all_results.items():
    for model_name, metrics in results.items():
        # Check for perfect or near-perfect scores
        if metrics.get('recall_1', 0) >= 0.99:
            suspicious_cases.append({
                'experiment': exp_name,
                'model': model_name,
                'issue': 'Near-perfect recall (≥99%)',
                'value': metrics['recall_1'],
                'fn': metrics.get('fn', 'N/A'),
                'tp': metrics.get('tp', 'N/A')
            })
        
        if metrics.get('precision_1', 0) >= 0.99:
            suspicious_cases.append({
                'experiment': exp_name,
                'model': model_name,
                'issue': 'Near-perfect precision (≥99%)',
                'value': metrics['precision_1'],
                'fp': metrics.get('fp', 'N/A'),
                'tp': metrics.get('tp', 'N/A')
            })
        
        if metrics.get('accuracy', 0) >= 0.99:
            suspicious_cases.append({
                'experiment': exp_name,
                'model': model_name,
                'issue': 'Near-perfect accuracy (≥99%)',
                'value': metrics['accuracy']
            })
        
        # Check for extreme imbalance in confusion matrix
        tp = metrics.get('tp', 0)
        fn = metrics.get('fn', 0)
        fp = metrics.get('fp', 0)
        tn = metrics.get('tn', 0)
        
        if fn == 0 and tp > 0:
            suspicious_cases.append({
                'experiment': exp_name,
                'model': model_name,
                'issue': 'Zero false negatives',
                'tp': tp,
                'fn': fn
            })
        
        if fp == 0 and tn > 0:
            suspicious_cases.append({
                'experiment': exp_name,
                'model': model_name,
                'issue': 'Zero false positives',
                'fp': fp,
                'tn': tn
            })

if suspicious_cases:
    print(f"\nFound {len(suspicious_cases)} suspicious cases:\n")
    for i, case in enumerate(suspicious_cases, 1):
        print(f"{i}. {case['experiment']} - {case['model']}")
        print(f"   Issue: {case['issue']}")
        for key, val in case.items():
            if key not in ['experiment', 'model', 'issue']:
                print(f"   {key}: {val}")
        print()
else:
    print("\nNo suspicious metrics detected.")

# ══════════════════════════════════════════════════════════════════════════════
# 3. PERFORMANCE VARIANCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PERFORMANCE VARIANCE ACROSS EXPERIMENTS")
print("=" * 80)

models = ['XGBoost', 'RandomForest', 'LogisticRegression']
metrics_to_check = ['accuracy', 'precision_1', 'recall_1', 'f1_1', 'roc_auc']

for model in models:
    print(f"\n{model}:")
    print("-" * 80)
    
    for metric in metrics_to_check:
        values = []
        for exp_name, results in all_results.items():
            if model in results and metric in results[model]:
                values.append(results[model][metric])
        
        if values:
            mean_val = np.mean(values)
            std_val = np.std(values)
            min_val = np.min(values)
            max_val = np.max(values)
            range_val = max_val - min_val
            
            # High variance might indicate overfitting in some experiments
            cv = (std_val / mean_val * 100) if mean_val > 0 else 0
            
            print(f"  {metric:20s}: mean={mean_val:.4f}, std={std_val:.4f}, "
                  f"range={range_val:.4f}, CV={cv:.1f}%")
            
            if cv > 10:
                print(f"    ⚠ High variance (CV > 10%) - possible overfitting in some experiments")

# ══════════════════════════════════════════════════════════════════════════════
# 4. TRAIN/TEST PERFORMANCE GAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("TRAIN/TEST PERFORMANCE GAP ANALYSIS")
print("=" * 80)

# Load dataset
data_path = os.path.join(OUTPUT_DIR, "gke_mixed_dataset.csv")
if os.path.exists(data_path):
    df = pd.read_csv(data_path)
    
    # Prepare data with one-hot encoding
    if 'pattern' in df.columns:
        df = df.drop(columns=['pattern'])
    
    service_dummies = pd.get_dummies(df['service'], prefix='service', dtype=int)
    df = df.drop(columns=['service'])
    df = pd.concat([df, service_dummies], axis=1)
    
    X = df.drop(columns=['sla_violated'])
    y = df['sla_violated']
    
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    print(f"\nDataset: {len(df)} samples, {len(X.columns)} features")
    print(f"Class distribution: {(y==0).sum()} no-violation, {(y==1).sum()} violation")
    
    # Perform 5-fold cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    print("\n5-Fold Cross-Validation Results:")
    print("-" * 80)
    
    models_cv = {
        'XGBoost': XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, 
                                 eval_metric='logloss', random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=200, max_depth=8, 
                                               class_weight='balanced', random_state=42),
        'LogisticRegression': LogisticRegression(class_weight='balanced', 
                                                 max_iter=1000, random_state=42)
    }
    
    cv_results = {}
    
    for model_name, model in models_cv.items():
        print(f"\n{model_name}:")
        
        # For Logistic Regression, scale features
        if model_name == 'LogisticRegression':
            from sklearn.pipeline import Pipeline
            model = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', model)
            ])
        
        # Cross-validation scores
        scores_acc = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
        scores_prec = cross_val_score(model, X, y, cv=cv, scoring='precision')
        scores_rec = cross_val_score(model, X, y, cv=cv, scoring='recall')
        scores_f1 = cross_val_score(model, X, y, cv=cv, scoring='f1')
        scores_roc = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
        
        cv_results[model_name] = {
            'accuracy': scores_acc,
            'precision': scores_prec,
            'recall': scores_rec,
            'f1': scores_f1,
            'roc_auc': scores_roc
        }
        
        print(f"  Accuracy:  {scores_acc.mean():.4f} ± {scores_acc.std():.4f}")
        print(f"  Precision: {scores_prec.mean():.4f} ± {scores_prec.std():.4f}")
        print(f"  Recall:    {scores_rec.mean():.4f} ± {scores_rec.std():.4f}")
        print(f"  F1-Score:  {scores_f1.mean():.4f} ± {scores_f1.std():.4f}")
        print(f"  ROC-AUC:   {scores_roc.mean():.4f} ± {scores_roc.std():.4f}")
        
        # Check for overfitting indicators
        if scores_acc.std() > 0.05:
            print(f"  ⚠ High variance in accuracy (std > 0.05)")
        if scores_f1.std() > 0.05:
            print(f"  ⚠ High variance in F1-score (std > 0.05)")
    
    # ══════════════════════════════════════════════════════════════════════════
    # 5. COMPARE CV RESULTS WITH SINGLE SPLIT RESULTS
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("COMPARISON: CROSS-VALIDATION vs SINGLE SPLIT")
    print("=" * 80)
    
    if 'Mixed One-Hot' in all_results:
        print("\nComparing with Mixed One-Hot experiment (single 80/20 split):\n")
        
        for model_name in models:
            if model_name in all_results['Mixed One-Hot']:
                single_split = all_results['Mixed One-Hot'][model_name]
                cv_mean = cv_results[model_name]
                
                print(f"{model_name}:")
                print(f"  {'Metric':<12} {'Single Split':>12} {'CV Mean':>12} {'Difference':>12}")
                print(f"  {'-'*50}")
                
                acc_diff = single_split['accuracy'] - cv_mean['accuracy'].mean()
                f1_diff = single_split['f1_1'] - cv_mean['f1'].mean()
                rec_diff = single_split['recall_1'] - cv_mean['recall'].mean()
                roc_diff = single_split['roc_auc'] - cv_mean['roc_auc'].mean()
                
                print(f"  {'Accuracy':<12} {single_split['accuracy']:>12.4f} "
                      f"{cv_mean['accuracy'].mean():>12.4f} {acc_diff:>12.4f}")
                print(f"  {'F1-Score':<12} {single_split['f1_1']:>12.4f} "
                      f"{cv_mean['f1'].mean():>12.4f} {f1_diff:>12.4f}")
                print(f"  {'Recall':<12} {single_split['recall_1']:>12.4f} "
                      f"{cv_mean['recall'].mean():>12.4f} {rec_diff:>12.4f}")
                print(f"  {'ROC-AUC':<12} {single_split['roc_auc']:>12.4f} "
                      f"{cv_mean['roc_auc'].mean():>12.4f} {roc_diff:>12.4f}")
                
                # Overfitting indicator
                if abs(acc_diff) > 0.05 or abs(f1_diff) > 0.05:
                    print(f"  ⚠ Large difference (>0.05) suggests possible overfitting")
                print()

print("\nNote: For detailed cross-validation analysis, models would need to be")
print("retrained with CV. Current analysis focuses on test set performance patterns.")
print("\nKey overfitting indicators to watch:")
print("  • Perfect or near-perfect metrics (recall/precision = 100%)")
print("  • Zero false negatives or false positives")
print("  • Large performance differences across similar experiments")

# ══════════════════════════════════════════════════════════════════════════════
# 5. SUMMARY AND RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("OVERFITTING ANALYSIS SUMMARY")
print("=" * 80)

print("\n1. SUSPICIOUS METRICS:")
if suspicious_cases:
    print(f"   Found {len(suspicious_cases)} cases with near-perfect or extreme metrics")
    print("   → Review these models carefully for potential overfitting")
else:
    print("   No suspicious metrics detected")

print("\n2. PERFORMANCE VARIANCE:")
print("   Check the variance analysis above")
print("   → High CV (>10%) suggests inconsistent performance across experiments")

print("\n3. CROSS-VALIDATION:")
print("   Compare CV results with single split results")
print("   → Large differences (>0.05) suggest overfitting to specific train/test split")

print("\n4. RECOMMENDATIONS:")
print("   • If single split >> CV: Model may be overfitting to that specific split")
print("   • If recall=100%: Check if model is too conservative (many false positives)")
print("   • If precision=100%: Check if model is too strict (many false negatives)")
print("   • High variance across experiments: Consider ensemble or more robust features")
print("   • For deployment: Use cross-validated performance as more realistic estimate")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
