"""
Phase 2a + 3 + 4: Standard 80/20 Split Training & Evaluation
Mirrors kafka-structured/ML-Models/train_models.py exactly,
applied to the GKE dataset for direct comparability.
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
    roc_auc_score, precision_recall_fscore_support
)
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(__file__)
DATA_PATH  = os.path.join(OUTPUT_DIR, "gke_combined.csv")
MODELS_DIR = os.path.join(OUTPUT_DIR, "models_standard")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS = [
    'service', 'request_rate_rps', 'error_rate_pct',
    'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
    'cpu_usage_pct', 'memory_usage_mb',
    'delta_rps', 'delta_p95_latency_ms', 'delta_cpu_usage_pct'
]
TARGET_COL = 'sla_violated'

# ── Load ──────────────────────────────────────────────────────────────────────
print("=" * 70)
print("PHASE 2a: STANDARD 80/20 SPLIT TRAINING")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
# Drop pattern column — not available at inference time
df = df.drop(columns=['pattern'])

X = df[FEATURE_COLS]
y = df[TARGET_COL]

print(f"\nDataset: {len(df)} rows")
print(f"Features: {FEATURE_COLS}")
print(f"Class distribution: 0={( y==0).sum()}  1={(y==1).sum()}  ({round((y==1).sum()/len(y)*100,2)}% violations)")

# ── Split ─────────────────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
print(f"\nTrain: {len(X_train)}  Test: {len(X_test)}")
print(f"Train violations: {y_train.sum()} ({round(y_train.sum()/len(y_train)*100,1)}%)")
print(f"Test violations:  {y_test.sum()} ({round(y_test.sum()/len(y_test)*100,1)}%)")

# ── SMOTE ─────────────────────────────────────────────────────────────────────
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_pos_weight = neg / pos

smote = SMOTE(random_state=42, sampling_strategy=1.0)
X_train_s, y_train_s = smote.fit_resample(X_train, y_train)

print(f"\nAfter SMOTE: {len(X_train_s)} training samples (50/50)")
print(f"scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

# ── Train ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE 3: MODEL TRAINING")
print("=" * 70)

model_xgb = XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    n_estimators=200, max_depth=6, learning_rate=0.1,
    eval_metric='logloss', random_state=42
)
model_xgb.fit(X_train_s, y_train_s)
print("XGBoost trained")

model_rf = RandomForestClassifier(
    n_estimators=200, max_depth=8,
    class_weight='balanced', random_state=42
)
model_rf.fit(X_train_s, y_train_s)
print("Random Forest trained")

model_lr = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', LogisticRegression(
        class_weight='balanced', max_iter=1000, random_state=42
    ))
])
model_lr.fit(X_train_s, y_train_s)
print("Logistic Regression trained")

# ── Evaluate ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE 4: EVALUATION — STANDARD SPLIT")
print("=" * 70)

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
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)

    print(f"\n{name}")
    print(classification_report(y_test, y_pred, target_names=['No Violation', 'Violation']))
    print(f"ROC-AUC: {roc:.4f}")
    print(f"Confusion Matrix:\n{cm}")

    results[name] = {
        'precision_0': round(prec[0], 4), 'recall_0': round(rec[0], 4), 'f1_0': round(f1[0], 4),
        'precision_1': round(prec[1], 4), 'recall_1': round(rec[1], 4), 'f1_1': round(f1[1], 4),
        'roc_auc': round(roc, 4),
        'tn': int(cm[0,0]), 'fp': int(cm[0,1]),
        'fn': int(cm[1,0]), 'tp': int(cm[1,1])
    }

# ── Feature importance ────────────────────────────────────────────────────────
for model_name, model, imp_attr in [
    ('xgb', model_xgb, 'feature_importances_'),
    ('rf',  model_rf,  'feature_importances_')
]:
    imps = getattr(model, imp_attr)
    idx  = np.argsort(imps)[::-1]
    plt.figure(figsize=(10, 6))
    plt.title(f'{"XGBoost" if model_name=="xgb" else "Random Forest"} Feature Importances (GKE)')
    plt.bar(range(len(imps)), imps[idx])
    plt.xticks(range(len(imps)), [FEATURE_COLS[i] for i in idx], rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'feature_importance_{model_name}_gke.png'), dpi=300)
    plt.close()

# ── Save models ───────────────────────────────────────────────────────────────
joblib.dump(model_xgb, os.path.join(MODELS_DIR, 'model_xgb.joblib'))
joblib.dump(model_rf,  os.path.join(MODELS_DIR, 'model_rf.joblib'))
joblib.dump(model_lr,  os.path.join(MODELS_DIR, 'model_lr.joblib'))

# ── Save results ──────────────────────────────────────────────────────────────
with open(os.path.join(OUTPUT_DIR, 'results_standard.json'), 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 70)
print("SUMMARY — STANDARD SPLIT")
print("=" * 70)
print(f"\n  {'Model':<22} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
print(f"  {'-'*60}")
for name, r in results.items():
    print(f"  {name:<22} {r['precision_1']:>8.4f} {r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")

print(f"\nModels saved to: {MODELS_DIR}")
print(f"Results saved to: results_standard.json")
