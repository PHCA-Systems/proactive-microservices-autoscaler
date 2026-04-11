"""
Retrain all 3 models with ONE-HOT ENCODED service feature
on the GKE Mixed 4-hour dataset.

This script:
1. Loads the GKE mixed 4-hour dataset
2. Applies one-hot encoding to the service feature
3. Trains XGBoost, Random Forest, and Logistic Regression
4. Produces comprehensive evaluation metrics
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
DATA_PATH = os.path.join(OUTPUT_DIR, "gke_mixed_dataset.csv")
MODELS_DIR = os.path.join(OUTPUT_DIR, "models_mixed_onehot")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET_COL = 'sla_violated'

print("=" * 80)
print("RETRAINING WITH ONE-HOT ENCODED SERVICE FEATURE")
print("=" * 80)
print("\nDataset: GKE Mixed 4-hour")
print("Approach: One-hot encode service feature")
print("Models: XGBoost, Random Forest, Logistic Regression")

# ── Load Data ─────────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("LOADING DATA")
print("-" * 80)

df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}")

# Drop pattern column (not available at inference time)
if 'pattern' in df.columns:
    df = df.drop(columns=['pattern'])
    print("Dropped 'pattern' column")

# Check service values
print(f"\nService unique values: {sorted(df['service'].unique())}")
print(f"Service value counts:\n{df['service'].value_counts().sort_index()}")

# ── One-Hot Encode Service ────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("ONE-HOT ENCODING SERVICE FEATURE")
print("-" * 80)

# One-hot encode service feature
service_dummies = pd.get_dummies(df['service'], prefix='service', dtype=int)
print(f"Created {len(service_dummies.columns)} one-hot encoded columns: {service_dummies.columns.tolist()}")

# Drop original service column and concatenate one-hot encoded columns
df = df.drop(columns=['service'])
df = pd.concat([df, service_dummies], axis=1)

# Define feature columns (all except target)
FEATURE_COLS = [col for col in df.columns if col != TARGET_COL]
print(f"\nTotal features: {len(FEATURE_COLS)}")
print(f"Features: {FEATURE_COLS}")

# Prepare X and y
X = df[FEATURE_COLS]
y = df[TARGET_COL]

# Handle NaN/inf values
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(0)

print(f"\nDataset shape: {X.shape}")
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
print(f"scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

# ── Train Models ──────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("TRAINING MODELS")
print("=" * 80)

# XGBoost
print("\n1. Training XGBoost...")
model_xgb = XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    eval_metric='logloss',
    random_state=42
)
model_xgb.fit(X_train_s, y_train_s)
print("   ✓ XGBoost trained")

# Random Forest
print("\n2. Training Random Forest...")
model_rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    class_weight='balanced',
    random_state=42
)
model_rf.fit(X_train_s, y_train_s)
print("   ✓ Random Forest trained")

# Logistic Regression
print("\n3. Training Logistic Regression...")
model_lr = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', LogisticRegression(
        class_weight='balanced',
        max_iter=1000,
        random_state=42
    ))
])
model_lr.fit(X_train_s, y_train_s)
print("   ✓ Logistic Regression trained")

# ── Evaluate Models ───────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("EVALUATION ON TEST SET")
print("=" * 80)

models = {
    'XGBoost': model_xgb,
    'RandomForest': model_rf,
    'LogisticRegression': model_lr
}

results = {}
for name, model in models.items():
    print(f"\n{name}")
    print("-" * 80)
    
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    cm = confusion_matrix(y_test, y_pred)
    roc = roc_auc_score(y_test, y_proba)
    acc = accuracy_score(y_test, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
    
    print(classification_report(y_test, y_pred, target_names=['No Violation', 'Violation']))
    print(f"Accuracy: {acc:.4f}")
    print(f"ROC-AUC:  {roc:.4f}")
    print(f"\nConfusion Matrix:")
    print(f"                 Predicted")
    print(f"                 No    Yes")
    print(f"Actual No    {cm[0,0]:6d} {cm[0,1]:6d}")
    print(f"Actual Yes   {cm[1,0]:6d} {cm[1,1]:6d}")
    
    results[name] = {
        'accuracy': round(acc, 4),
        'precision_0': round(prec[0], 4),
        'recall_0': round(rec[0], 4),
        'f1_0': round(f1[0], 4),
        'precision_1': round(prec[1], 4),
        'recall_1': round(rec[1], 4),
        'f1_1': round(f1[1], 4),
        'roc_auc': round(roc, 4),
        'tn': int(cm[0,0]),
        'fp': int(cm[0,1]),
        'fn': int(cm[1,0]),
        'tp': int(cm[1,1])
    }

# ── Feature Importance ────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("FEATURE IMPORTANCE")
print("=" * 80)

for model_name, model, imp_attr in [
    ('xgb', model_xgb, 'feature_importances_'),
    ('rf',  model_rf,  'feature_importances_')
]:
    imps = getattr(model, imp_attr)
    idx  = np.argsort(imps)[::-1]
    
    print(f"\n{model_name.upper()} Top 15 Features:")
    for i, feat_idx in enumerate(idx[:15], 1):
        print(f"  {i:2d}. {FEATURE_COLS[feat_idx]:30s}: {imps[feat_idx]:.4f}")
    
    # Plot
    plt.figure(figsize=(12, 8))
    plt.title(f'{"XGBoost" if model_name=="xgb" else "Random Forest"} Feature Importances\n(GKE Mixed with One-Hot Encoded Service)')
    top_n = min(20, len(imps))
    plt.bar(range(top_n), imps[idx[:top_n]])
    plt.xticks(range(top_n), [FEATURE_COLS[i] for i in idx[:top_n]], rotation=45, ha='right')
    plt.ylabel('Importance')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'feature_importance_{model_name}_mixed_onehot.png'), dpi=300)
    plt.close()
    print(f"   Saved: feature_importance_{model_name}_mixed_onehot.png")

# ── Save Models ───────────────────────────────────────────────────────────────
print("\n" + "-" * 80)
print("SAVING MODELS")
print("-" * 80)

joblib.dump(model_xgb, os.path.join(MODELS_DIR, 'model_xgb.joblib'))
print(f"Saved: {os.path.join(MODELS_DIR, 'model_xgb.joblib')}")

joblib.dump(model_rf, os.path.join(MODELS_DIR, 'model_rf.joblib'))
print(f"Saved: {os.path.join(MODELS_DIR, 'model_rf.joblib')}")

joblib.dump(model_lr, os.path.join(MODELS_DIR, 'model_lr.joblib'))
print(f"Saved: {os.path.join(MODELS_DIR, 'model_lr.joblib')}")

# ── Save Results ──────────────────────────────────────────────────────────────
results_path = os.path.join(OUTPUT_DIR, 'results_mixed_onehot.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"Saved: {results_path}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SUMMARY: GKE MIXED WITH ONE-HOT ENCODED SERVICE")
print("=" * 80)

print(f"\n  {'Model':<22} {'Accuracy':>9} {'Prec(1)':>8} {'Rec(1)':>8} {'F1(1)':>8} {'ROC-AUC':>9}")
print(f"  {'-'*70}")
for name, r in results.items():
    print(f"  {name:<22} {r['accuracy']:>9.4f} {r['precision_1']:>8.4f} {r['recall_1']:>8.4f} {r['f1_1']:>8.4f} {r['roc_auc']:>9.4f}")

print("\n" + "=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)
print(f"\nModels saved to: {MODELS_DIR}")
print(f"Results saved to: {results_path}")
print(f"Feature importance plots saved to: {OUTPUT_DIR}")
