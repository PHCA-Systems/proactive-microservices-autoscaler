"""
Train Additional Models: LightGBM and SVM
on GKE Mixed 4-hour dataset with one-hot encoded service feature
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
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_fscore_support, accuracy_score
)
from imblearn.over_sampling import SMOTE
from lightgbm import LGBMClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(OUTPUT_DIR, "gke_mixed_dataset.csv")
MODELS_DIR = os.path.join(OUTPUT_DIR, "models_additional")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET_COL = 'sla_violated'

print("=" * 80)
print("TRAINING ADDITIONAL MODELS: LightGBM & SVM")
print("=" * 80)
print("\nDataset: GKE Mixed 4-hour")
print("Feature Engineering: One-hot encoded service")
print("Models: LightGBM, SVM (RBF kernel)")

# ── Load Data ─────────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("LOADING DATA")
print("-" * 80)

df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} rows")

# Drop pattern column
if 'pattern' in df.columns:
    df = df.drop(columns=['pattern'])
    print("Dropped 'pattern' column")

# One-hot encode service
service_dummies = pd.get_dummies(df['service'], prefix='service', dtype=int)
print(f"Created {len(service_dummies.columns)} one-hot encoded service columns")

df = df.drop(columns=['service'])
df = pd.concat([df, service_dummies], axis=1)

# Prepare features
FEATURE_COLS = [col for col in df.columns if col != TARGET_COL]
X = df[FEATURE_COLS]
y = df[TARGET_COL]

# Handle NaN/inf
X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

print(f"\nDataset shape: {X.shape}")
print(f"Features: {len(FEATURE_COLS)}")
print(f"Class distribution: 0={( y==0).sum()}  1={(y==1).sum()}  ({round((y==1).sum()/len(y)*100,2)}% violations)")

# ── Split Data ────────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("TRAIN/TEST SPLIT (80/20)")
print("-" * 80)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"Train: {len(X_train)} samples")
print(f"Test:  {len(X_test)} samples")
print(f"Train violations: {y_train.sum()} ({round(y_train.sum()/len(y_train)*100,1)}%)")
print(f"Test violations:  {y_test.sum()} ({round(y_test.sum()/len(y_test)*100,1)}%)")

# ── Apply SMOTE ───────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("APPLYING SMOTE")
print("-" * 80)

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_pos_weight = neg / pos

smote = SMOTE(random_state=42, sampling_strategy=1.0)
X_train_s, y_train_s = smote.fit_resample(X_train, y_train)

print(f"Before SMOTE: {len(X_train)} samples (0={neg}, 1={pos})")
print(f"After SMOTE:  {len(X_train_s)} samples (50/50 split)")
print(f"scale_pos_weight: {scale_pos_weight:.2f}")

# ── Train Models ──────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("TRAINING MODELS")
print("=" * 80)

# 1. LightGBM
print("\n1. Training LightGBM...")
print("   Configuration:")
print("   - n_estimators: 200")
print("   - max_depth: 6")
print("   - learning_rate: 0.1")
print("   - scale_pos_weight: {:.2f}".format(scale_pos_weight))
print("   - class_weight: balanced")

model_lgb = LGBMClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    class_weight='balanced',
    random_state=42,
    verbose=-1
)
model_lgb.fit(X_train_s, y_train_s)
print("   ✓ LightGBM trained")

# 2. SVM
print("\n2. Training SVM (RBF kernel)...")
print("   Configuration:")
print("   - kernel: RBF")
print("   - class_weight: balanced")
print("   - probability: True (for ROC-AUC)")
print("   Note: SVM training may take a few minutes...")

# Scale features for SVM
scaler = StandardScaler()
X_train_s_scaled = scaler.fit_transform(X_train_s)
X_test_scaled = scaler.transform(X_test)

model_svm = SVC(
    kernel='rbf',
    class_weight='balanced',
    probability=True,
    random_state=42
)
model_svm.fit(X_train_s_scaled, y_train_s)
print("   ✓ SVM trained")

# ── Evaluate Models ───────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("EVALUATION ON TEST SET")
print("=" * 80)

results = {}

# Evaluate LightGBM
print("\nLightGBM")
print("-" * 80)

y_pred_lgb = model_lgb.predict(X_test)
y_proba_lgb = model_lgb.predict_proba(X_test)[:, 1]

cm_lgb = confusion_matrix(y_test, y_pred_lgb)
roc_lgb = roc_auc_score(y_test, y_proba_lgb)
acc_lgb = accuracy_score(y_test, y_pred_lgb)
prec_lgb, rec_lgb, f1_lgb, _ = precision_recall_fscore_support(y_test, y_pred_lgb, average=None)

print(classification_report(y_test, y_pred_lgb, target_names=['No Violation', 'Violation']))
print(f"Accuracy: {acc_lgb:.4f}")
print(f"ROC-AUC:  {roc_lgb:.4f}")
print(f"\nConfusion Matrix:")
print(f"                 Predicted")
print(f"                 No    Yes")
print(f"Actual No    {cm_lgb[0,0]:6d} {cm_lgb[0,1]:6d}")
print(f"Actual Yes   {cm_lgb[1,0]:6d} {cm_lgb[1,1]:6d}")

results['LightGBM'] = {
    'accuracy': round(acc_lgb, 4),
    'precision_0': round(prec_lgb[0], 4),
    'recall_0': round(rec_lgb[0], 4),
    'f1_0': round(f1_lgb[0], 4),
    'precision_1': round(prec_lgb[1], 4),
    'recall_1': round(rec_lgb[1], 4),
    'f1_1': round(f1_lgb[1], 4),
    'roc_auc': round(roc_lgb, 4),
    'tn': int(cm_lgb[0,0]),
    'fp': int(cm_lgb[0,1]),
    'fn': int(cm_lgb[1,0]),
    'tp': int(cm_lgb[1,1])
}

# Evaluate SVM
print("\nSVM (RBF)")
print("-" * 80)

y_pred_svm = model_svm.predict(X_test_scaled)
y_proba_svm = model_svm.predict_proba(X_test_scaled)[:, 1]

cm_svm = confusion_matrix(y_test, y_pred_svm)
roc_svm = roc_auc_score(y_test, y_proba_svm)
acc_svm = accuracy_score(y_test, y_pred_svm)
prec_svm, rec_svm, f1_svm, _ = precision_recall_fscore_support(y_test, y_pred_svm, average=None)

print(classification_report(y_test, y_pred_svm, target_names=['No Violation', 'Violation']))
print(f"Accuracy: {acc_svm:.4f}")
print(f"ROC-AUC:  {roc_svm:.4f}")
print(f"\nConfusion Matrix:")
print(f"                 Predicted")
print(f"                 No    Yes")
print(f"Actual No    {cm_svm[0,0]:6d} {cm_svm[0,1]:6d}")
print(f"Actual Yes   {cm_svm[1,0]:6d} {cm_svm[1,1]:6d}")

results['SVM'] = {
    'accuracy': round(acc_svm, 4),
    'precision_0': round(prec_svm[0], 4),
    'recall_0': round(rec_svm[0], 4),
    'f1_0': round(f1_svm[0], 4),
    'precision_1': round(prec_svm[1], 4),
    'recall_1': round(rec_svm[1], 4),
    'f1_1': round(f1_svm[1], 4),
    'roc_auc': round(roc_svm, 4),
    'tn': int(cm_svm[0,0]),
    'fp': int(cm_svm[0,1]),
    'fn': int(cm_svm[1,0]),
    'tp': int(cm_svm[1,1])
}

# ── Feature Importance (LightGBM only) ────────────────────────────────────────
print("\n" + "=" * 80)
print("FEATURE IMPORTANCE (LightGBM)")
print("=" * 80)

imps = model_lgb.feature_importances_
idx = np.argsort(imps)[::-1]

print("\nTop 15 Features:")
for i, feat_idx in enumerate(idx[:15], 1):
    print(f"  {i:2d}. {FEATURE_COLS[feat_idx]:30s}: {imps[feat_idx]:.4f}")

# Plot
plt.figure(figsize=(12, 8))
plt.title('LightGBM Feature Importances\n(GKE Mixed with One-Hot Encoded Service)')
top_n = min(20, len(imps))
plt.bar(range(top_n), imps[idx[:top_n]])
plt.xticks(range(top_n), [FEATURE_COLS[i] for i in idx[:top_n]], rotation=45, ha='right')
plt.ylabel('Importance')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'feature_importance_lgb_mixed_onehot.png'), dpi=300)
plt.close()
print("\nSaved: feature_importance_lgb_mixed_onehot.png")

# ── Save Models ───────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("SAVING MODELS")
print("-" * 80)

joblib.dump(model_lgb, os.path.join(MODELS_DIR, 'model_lgb.joblib'))
print(f"Saved: {os.path.join(MODELS_DIR, 'model_lgb.joblib')}")

# Save SVM with scaler in a pipeline
svm_pipeline = Pipeline([
    ('scaler', scaler),
    ('svm', model_svm)
])
joblib.dump(svm_pipeline, os.path.join(MODELS_DIR, 'model_svm.joblib'))
print(f"Saved: {os.path.join(MODELS_DIR, 'model_svm.joblib')}")

# ── Save Results ──────────────────────────────────────────────────────────────
results_path = os.path.join(OUTPUT_DIR, 'results_additional_models.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"Saved: {results_path}")

# ── Compare with Existing Models ──────────────────────────────────────────────
print("\n" + "=" * 80)
print("COMPARISON WITH EXISTING MODELS")
print("=" * 80)

# Load existing results
existing_results_path = os.path.join(OUTPUT_DIR, 'results_mixed_onehot.json')
if os.path.exists(existing_results_path):
    with open(existing_results_path, 'r') as f:
        existing_results = json.load(f)
    
    all_models = {**existing_results, **results}
    
    print(f"\n  {'Model':<22} {'Accuracy':>9} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
    print(f"  {'-'*70}")
    
    for name in ['XGBoost', 'RandomForest', 'LogisticRegression', 'LightGBM', 'SVM']:
        if name in all_models:
            r = all_models[name]
            print(f"  {name:<22} {r['accuracy']:>9.4f} {r['precision_1']:>8.4f} "
                  f"{r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")
    
    # Find best model
    print("\n" + "-" * 80)
    print("BEST PERFORMERS")
    print("-" * 80)
    
    best_f1 = max(all_models.items(), key=lambda x: x[1]['f1_1'])
    best_roc = max(all_models.items(), key=lambda x: x[1]['roc_auc'])
    best_recall = max(all_models.items(), key=lambda x: x[1]['recall_1'])
    best_precision = max(all_models.items(), key=lambda x: x[1]['precision_1'])
    
    print(f"\nBest F1-Score:   {best_f1[0]:<22} ({best_f1[1]['f1_1']:.4f})")
    print(f"Best ROC-AUC:    {best_roc[0]:<22} ({best_roc[1]['roc_auc']:.4f})")
    print(f"Best Recall:     {best_recall[0]:<22} ({best_recall[1]['recall_1']:.4f})")
    print(f"Best Precision:  {best_precision[0]:<22} ({best_precision[1]['precision_1']:.4f})")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SUMMARY: ADDITIONAL MODELS")
print("=" * 80)

print(f"\n  {'Model':<22} {'Accuracy':>9} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
print(f"  {'-'*70}")
for name, r in results.items():
    print(f"  {name:<22} {r['accuracy']:>9.4f} {r['precision_1']:>8.4f} "
          f"{r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")

print("\n" + "=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)
print(f"\nModels saved to: {MODELS_DIR}")
print(f"Results saved to: {results_path}")
print(f"Feature importance plot: feature_importance_lgb_mixed_onehot.png")
