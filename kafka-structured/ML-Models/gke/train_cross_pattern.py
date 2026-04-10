"""
Phase 2b + 3 + 4: Cross-Pattern Leave-One-Out Evaluation
Trains on 3 patterns, tests on the held-out 4th.
Repeated for all 4 combinations to assess generalization.
"""

import os
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_fscore_support
)
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(__file__)
DATA_PATH  = os.path.join(OUTPUT_DIR, "gke_combined.csv")
MODELS_DIR = os.path.join(OUTPUT_DIR, "models_cross_pattern")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS = [
    'service', 'request_rate_rps', 'error_rate_pct',
    'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
    'cpu_usage_pct', 'memory_usage_mb',
    'delta_rps', 'delta_p95_latency_ms', 'delta_cpu_usage_pct'
]
TARGET_COL = 'sla_violated'
PATTERNS   = ['constant', 'ramp', 'spike', 'step']

print("=" * 70)
print("PHASE 2b: CROSS-PATTERN LEAVE-ONE-OUT EVALUATION")
print("=" * 70)

df = pd.read_csv(DATA_PATH)

all_results = {}

for held_out in PATTERNS:
    train_patterns = [p for p in PATTERNS if p != held_out]
    print(f"\n{'='*70}")
    print(f"Hold-out: {held_out.upper()}  |  Train: {', '.join(train_patterns)}")
    print(f"{'='*70}")

    train_df = df[df['pattern'].isin(train_patterns)]
    test_df  = df[df['pattern'] == held_out]

    X_train = train_df[FEATURE_COLS]
    y_train = train_df[TARGET_COL]
    X_test  = test_df[FEATURE_COLS]
    y_test  = test_df[TARGET_COL]

    print(f"Train: {len(X_train)} rows  ({y_train.sum()} violations, {round(y_train.sum()/len(y_train)*100,1)}%)")
    print(f"Test:  {len(X_test)} rows  ({y_test.sum()} violations, {round(y_test.sum()/len(y_test)*100,1)}%)")

    # SMOTE on train only
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    smote = SMOTE(random_state=42, sampling_strategy=1.0)
    X_train_s, y_train_s = smote.fit_resample(X_train, y_train)
    print(f"After SMOTE: {len(X_train_s)} training samples")

    # Train
    model_xgb = XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        n_estimators=200, max_depth=6, learning_rate=0.1,
        eval_metric='logloss', random_state=42
    )
    model_xgb.fit(X_train_s, y_train_s)

    model_rf = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced', random_state=42
    )
    model_rf.fit(X_train_s, y_train_s)

    model_lr = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(
            class_weight='balanced', max_iter=1000, random_state=42
        ))
    ])
    model_lr.fit(X_train_s, y_train_s)

    # Evaluate
    fold_results = {}
    models = {
        'XGBoost': model_xgb,
        'RandomForest': model_rf,
        'LogisticRegression': model_lr
    }

    for name, model in models.items():
        y_pred  = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        cm      = confusion_matrix(y_test, y_pred)
        roc     = roc_auc_score(y_test, y_proba) if y_test.sum() > 0 else 0.0
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None, zero_division=0)

        print(f"\n  {name}")
        print(classification_report(y_test, y_pred, target_names=['No Violation', 'Violation'], zero_division=0))
        print(f"  ROC-AUC: {roc:.4f}")

        fold_results[name] = {
            'precision_1': round(float(prec[1]), 4) if len(prec) > 1 else 0,
            'recall_1':    round(float(rec[1]),  4) if len(rec)  > 1 else 0,
            'f1_1':        round(float(f1[1]),   4) if len(f1)   > 1 else 0,
            'roc_auc':     round(roc, 4),
            'tn': int(cm[0,0]), 'fp': int(cm[0,1]),
            'fn': int(cm[1,0]), 'tp': int(cm[1,1])
        }

        # Save model for this fold
        joblib.dump(model, os.path.join(MODELS_DIR, f'model_{name.lower().replace(" ","_")}_holdout_{held_out}.joblib'))

    all_results[held_out] = fold_results

# ── Aggregate summary ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CROSS-PATTERN SUMMARY")
print("=" * 70)

for model_name in ['XGBoost', 'RandomForest', 'LogisticRegression']:
    print(f"\n  {model_name}")
    print(f"  {'Hold-out':<12} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
    print(f"  {'-'*50}")
    precs, recs, f1s, rocs = [], [], [], []
    for held_out in PATTERNS:
        r = all_results[held_out][model_name]
        precs.append(r['precision_1']); recs.append(r['recall_1'])
        f1s.append(r['f1_1']); rocs.append(r['roc_auc'])
        print(f"  {held_out:<12} {r['precision_1']:>8.4f} {r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")
    print(f"  {'MEAN':<12} {np.mean(precs):>8.4f} {np.mean(recs):>8.4f} {np.mean(f1s):>8.4f} {np.mean(rocs):>9.4f}")
    print(f"  {'STD':<12} {np.std(precs):>8.4f} {np.std(recs):>8.4f} {np.std(f1s):>8.4f} {np.std(rocs):>9.4f}")

# ── Save ──────────────────────────────────────────────────────────────────────
with open(os.path.join(OUTPUT_DIR, 'results_cross_pattern.json'), 'w') as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to: results_cross_pattern.json")
