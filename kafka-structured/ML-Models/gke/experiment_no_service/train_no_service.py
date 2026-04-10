"""
Experiment: Training models WITHOUT the service feature
to see if other features become more important and how performance changes.

This experiment tests whether the service feature is causing data leakage
or if it's genuinely predictive.
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_fscore_support, accuracy_score
)
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Load both datasets
GKE_SEPARATED_PATH = os.path.join(OUTPUT_DIR, "../gke_separated_dataset.csv")
GKE_MIXED_PATH = os.path.join(OUTPUT_DIR, "../gke_mixed_dataset.csv")
LOCAL_PATH = os.path.join(OUTPUT_DIR, "../../../data/local/mixed_4hour_metrics.csv")

# Features WITHOUT service
FEATURE_COLS = [
    'request_rate_rps', 'error_rate_pct',
    'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
    'cpu_usage_pct', 'memory_usage_mb',
    'delta_rps', 'delta_p95_latency_ms', 'delta_cpu_usage_pct'
]
TARGET_COL = 'sla_violated'

print("=" * 80)
print("EXPERIMENT: TRAINING WITHOUT SERVICE FEATURE")
print("=" * 80)
print("\nHypothesis: Service feature may be acting as a proxy for the target")
print("Testing: How do models perform when forced to learn from metrics alone?")
print("\nFeatures used (10 total):")
for i, feat in enumerate(FEATURE_COLS, 1):
    print(f"  {i:2d}. {feat}")

def preprocess_local_data(df):
    """Preprocess local dataset (service is string)"""
    df = df.copy()
    # Drop timestamp and service
    df = df.drop(columns=['timestamp', 'service'])
    # Handle NaN/inf
    numeric_cols = FEATURE_COLS
    df = df.replace([np.inf, -np.inf], np.nan)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    return df

def preprocess_gke_data(df):
    """Preprocess GKE dataset (service is already encoded)"""
    df = df.copy()
    # Drop service and pattern columns
    if 'pattern' in df.columns:
        df = df.drop(columns=['pattern'])
    df = df.drop(columns=['service'])
    # Handle NaN/inf
    numeric_cols = FEATURE_COLS
    df = df.replace([np.inf, -np.inf], np.nan)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    return df

def train_and_evaluate(X, y, dataset_name):
    """Train and evaluate all three models"""
    print("\n" + "=" * 80)
    print(f"TRAINING ON: {dataset_name}")
    print("=" * 80)
    
    print(f"\nDataset: {len(X)} rows, {len(FEATURE_COLS)} features")
    print(f"Class distribution: 0={( y==0).sum()}  1={(y==1).sum()}  ({round((y==1).sum()/len(y)*100,2)}% violations)")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"\nTrain: {len(X_train)}  Test: {len(X_test)}")
    print(f"Train violations: {y_train.sum()} ({round(y_train.sum()/len(y_train)*100,1)}%)")
    print(f"Test violations:  {y_test.sum()} ({round(y_test.sum()/len(y_test)*100,1)}%)")
    
    # SMOTE
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = neg / pos
    
    smote = SMOTE(random_state=42, sampling_strategy=1.0)
    X_train_s, y_train_s = smote.fit_resample(X_train, y_train)
    
    print(f"\nAfter SMOTE: {len(X_train_s)} training samples (50/50)")
    print(f"scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")
    
    # Train models
    print("\n" + "-" * 80)
    print("TRAINING MODELS")
    print("-" * 80)
    
    model_xgb = XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        n_estimators=200, max_depth=6, learning_rate=0.1,
        eval_metric='logloss', random_state=42
    )
    model_xgb.fit(X_train_s, y_train_s)
    print("✓ XGBoost trained")
    
    model_rf = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced', random_state=42
    )
    model_rf.fit(X_train_s, y_train_s)
    print("✓ Random Forest trained")
    
    model_lr = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(
            class_weight='balanced', max_iter=1000, random_state=42
        ))
    ])
    model_lr.fit(X_train_s, y_train_s)
    print("✓ Logistic Regression trained")
    
    # Evaluate
    print("\n" + "-" * 80)
    print("EVALUATION")
    print("-" * 80)
    
    models = {
        'XGBoost': model_xgb,
        'RandomForest': model_rf,
        'LogisticRegression': model_lr
    }
    
    results = {}
    for name, model in models.items():
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        cm = confusion_matrix(y_test, y_pred)
        roc = roc_auc_score(y_test, y_proba)
        acc = accuracy_score(y_test, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
        
        print(f"\n{name}")
        print(classification_report(y_test, y_pred, target_names=['No Violation', 'Violation']))
        print(f"Accuracy: {acc:.4f}")
        print(f"ROC-AUC: {roc:.4f}")
        print(f"Confusion Matrix:\n{cm}")
        
        results[name] = {
            'accuracy': round(acc, 4),
            'precision_0': round(prec[0], 4), 'recall_0': round(rec[0], 4), 'f1_0': round(f1[0], 4),
            'precision_1': round(prec[1], 4), 'recall_1': round(rec[1], 4), 'f1_1': round(f1[1], 4),
            'roc_auc': round(roc, 4),
            'tn': int(cm[0,0]), 'fp': int(cm[0,1]),
            'fn': int(cm[1,0]), 'tp': int(cm[1,1])
        }
    
    # Feature importance
    print("\n" + "-" * 80)
    print("FEATURE IMPORTANCE")
    print("-" * 80)
    
    for model_name, model, imp_attr in [
        ('xgb', model_xgb, 'feature_importances_'),
        ('rf',  model_rf,  'feature_importances_')
    ]:
        imps = getattr(model, imp_attr)
        idx  = np.argsort(imps)[::-1]
        
        print(f"\n{model_name.upper()} Feature Importances:")
        for i in idx:
            print(f"  {FEATURE_COLS[i]:25s}: {imps[i]:.4f}")
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.title(f'{"XGBoost" if model_name=="xgb" else "Random Forest"} Feature Importances (No Service)\n{dataset_name}')
        plt.bar(range(len(imps)), imps[idx])
        plt.xticks(range(len(imps)), [FEATURE_COLS[i] for i in idx], rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'feature_importance_{model_name}_{dataset_name.lower().replace(" ", "_")}.png'), dpi=300)
        plt.close()
    
    # Save models
    dataset_suffix = dataset_name.lower().replace(" ", "_")
    joblib.dump(model_xgb, os.path.join(MODELS_DIR, f'model_xgb_{dataset_suffix}.joblib'))
    joblib.dump(model_rf,  os.path.join(MODELS_DIR, f'model_rf_{dataset_suffix}.joblib'))
    joblib.dump(model_lr,  os.path.join(MODELS_DIR, f'model_lr_{dataset_suffix}.joblib'))
    
    return results

# ============================================================================
# TRAIN ON ALL THREE DATASETS
# ============================================================================

all_results = {}

# 1. GKE Separated
print("\n" + "=" * 80)
print("DATASET 1: GKE SEPARATED")
print("=" * 80)
df_gke_sep = pd.read_csv(GKE_SEPARATED_PATH)
df_gke_sep = preprocess_gke_data(df_gke_sep)
X_gke_sep = df_gke_sep[FEATURE_COLS]
y_gke_sep = df_gke_sep[TARGET_COL]
all_results['GKE_Separated'] = train_and_evaluate(X_gke_sep, y_gke_sep, "GKE Separated")

# 2. GKE Mixed
print("\n" + "=" * 80)
print("DATASET 2: GKE MIXED")
print("=" * 80)
df_gke_mix = pd.read_csv(GKE_MIXED_PATH)
df_gke_mix = preprocess_gke_data(df_gke_mix)
X_gke_mix = df_gke_mix[FEATURE_COLS]
y_gke_mix = df_gke_mix[TARGET_COL]
all_results['GKE_Mixed'] = train_and_evaluate(X_gke_mix, y_gke_mix, "GKE Mixed")

# 3. Local
print("\n" + "=" * 80)
print("DATASET 3: LOCAL")
print("=" * 80)
df_local = pd.read_csv(LOCAL_PATH)
df_local = preprocess_local_data(df_local)
X_local = df_local[FEATURE_COLS]
y_local = df_local[TARGET_COL]
all_results['Local'] = train_and_evaluate(X_local, y_local, "Local")

# ============================================================================
# SAVE RESULTS
# ============================================================================

with open(os.path.join(OUTPUT_DIR, 'results_no_service.json'), 'w') as f:
    json.dump(all_results, f, indent=2)

# ============================================================================
# SUMMARY COMPARISON
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY: ALL DATASETS WITHOUT SERVICE FEATURE")
print("=" * 80)

for dataset_name, results in all_results.items():
    print(f"\n{dataset_name}")
    print("-" * 80)
    print(f"  {'Model':<22} {'Accuracy':>9} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
    print(f"  {'-'*70}")
    for model_name, r in results.items():
        print(f"  {model_name:<22} {r['accuracy']:>9.4f} {r['precision_1']:>8.4f} {r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")

print("\n" + "=" * 80)
print("EXPERIMENT COMPLETE")
print("=" * 80)
print(f"\nResults saved to: {os.path.join(OUTPUT_DIR, 'results_no_service.json')}")
print(f"Models saved to: {MODELS_DIR}")
print(f"Feature importance plots saved to: {OUTPUT_DIR}")
