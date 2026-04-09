"""
SLA Violation Prediction Model Training Script

This script trains three classification models (XGBoost, Random Forest, Logistic Regression)
to predict SLA violations from service metrics during load ramp-up scenarios.

Key design decisions:
- SMOTE is applied ONLY to training data to handle 16.5% class imbalance
- Test set remains untouched to provide unbiased performance estimates
- Recall for class 1 (violations) is prioritized over precision
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. PREPROCESSING
# ============================================================================

print("=" * 80)
print("STEP 1: DATA PREPROCESSING")
print("=" * 80)

# Load data
df = pd.read_csv('hour_ramp_metrics.csv')
print(f"\nLoaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

# Drop timestamp column
df = df.drop('timestamp', axis=1)
print("Dropped 'timestamp' column")

# Label-encode service column with fixed mapping (deterministic for inference)
service_mapping = {
    'catalogue': 0,
    'carts': 1,
    'front-end': 2,
    'orders': 3,
    'payment': 4,
    'shipping': 5,
    'user': 6
}
df['service'] = df['service'].map(service_mapping)
print(f"Label-encoded 'service' column using fixed mapping: {service_mapping}")

# Check for NaN and inf values
print(f"\nNaN values per column:\n{df.isnull().sum()}")
print(f"\nInf values detected: {np.isinf(df.select_dtypes(include=[np.number])).sum().sum()}")

# Fill NaN and inf with 0 (common in delta_* columns for first polling window)
df = df.replace([np.inf, -np.inf], np.nan)
df = df.fillna(0)
print("Filled all NaN and inf values with 0")

# Define features and target
X = df.drop('sla_violated', axis=1)
y = df['sla_violated']

print(f"\nFeatures shape: {X.shape}")
print(f"Target shape: {y.shape}")
print(f"Feature columns: {list(X.columns)}")

# ============================================================================
# 2. TRAIN/TEST SPLIT & CLASS IMBALANCE HANDLING
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: TRAIN/TEST SPLIT & SMOTE")
print("=" * 80)

# Stratified split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"\nTrain set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")

# Class distribution before SMOTE
print(f"\nOriginal training set class distribution:")
print(f"  Class 0 (no violation): {(y_train == 0).sum()} ({(y_train == 0).sum() / len(y_train) * 100:.1f}%)")
print(f"  Class 1 (violation):    {(y_train == 1).sum()} ({(y_train == 1).sum() / len(y_train) * 100:.1f}%)")

# Calculate scale_pos_weight for XGBoost (before SMOTE)
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count
print(f"\nScale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

# Apply SMOTE to training set only
# CRITICAL: Test set must remain untouched to provide unbiased performance estimates
# for thesis validity. SMOTE on test data would artificially inflate metrics.
smote = SMOTE(random_state=42, sampling_strategy=1.0)  # 1.0 = 50/50 balance
X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

print(f"\nAfter SMOTE training set class distribution:")
print(f"  Class 0 (no violation): {(y_train_smote == 0).sum()} ({(y_train_smote == 0).sum() / len(y_train_smote) * 100:.1f}%)")
print(f"  Class 1 (violation):    {(y_train_smote == 1).sum()} ({(y_train_smote == 1).sum() / len(y_train_smote) * 100:.1f}%)")
print(f"Training set size after SMOTE: {X_train_smote.shape[0]} samples")

# ============================================================================
# 3. TRAIN THREE MODELS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: MODEL TRAINING")
print("=" * 80)

# Model A: XGBoost
print("\nTraining Model A: XGBoost...")
model_xgb = XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    use_label_encoder=False,
    eval_metric='logloss',
    random_state=42
)
model_xgb.fit(X_train_smote, y_train_smote)
print("✓ XGBoost trained")

# Model B: Random Forest
print("\nTraining Model B: Random Forest...")
model_rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    class_weight='balanced',
    random_state=42
)
model_rf.fit(X_train_smote, y_train_smote)
print("✓ Random Forest trained")

# Model C: Logistic Regression with StandardScaler
print("\nTraining Model C: Logistic Regression (with StandardScaler)...")
model_lr = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', LogisticRegression(
        class_weight='balanced',
        max_iter=1000,
        random_state=42
    ))
])
model_lr.fit(X_train_smote, y_train_smote)
print("✓ Logistic Regression trained")

# ============================================================================
# 4. EVALUATE ALL MODELS ON TEST SET
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: MODEL EVALUATION ON TEST SET")
print("=" * 80)

models = {
    'XGBoost': model_xgb,
    'Random Forest': model_rf,
    'Logistic Regression': model_lr
}

results = {}

for name, model in models.items():
    print(f"\n{'=' * 80}")
    print(f"MODEL: {name}")
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
    
    # Extract metrics for summary
    from sklearn.metrics import precision_recall_fscore_support
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
    results[name] = {
        'Precision(1)': precision[1],
        'Recall(1)': recall[1],
        'F1(1)': f1[1],
        'ROC-AUC': roc_auc
    }
    
    # Commentary on recall
    print(f"\n📊 Recall Analysis:")
    print(f"   Recall for class 1 (violations): {recall[1]:.3f}")
    print(f"   This means {recall[1]*100:.1f}% of actual violations were detected.")
    print(f"   False negatives (missed violations): {cm[1, 0]} out of {cm[1, 0] + cm[1, 1]}")

# ============================================================================
# 5. FEATURE IMPORTANCE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 5: FEATURE IMPORTANCE ANALYSIS")
print("=" * 80)

feature_names = X.columns.tolist()

# XGBoost feature importance
print("\nGenerating XGBoost feature importance plot...")
xgb_importances = model_xgb.feature_importances_
xgb_indices = np.argsort(xgb_importances)[::-1]

plt.figure(figsize=(10, 6))
plt.title('XGBoost Feature Importances', fontsize=14, fontweight='bold')
plt.bar(range(len(xgb_importances)), xgb_importances[xgb_indices])
plt.xticks(range(len(xgb_importances)), [feature_names[i] for i in xgb_indices], rotation=45, ha='right')
plt.xlabel('Features')
plt.ylabel('Importance')
plt.tight_layout()
plt.savefig('feature_importance_xgb.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: feature_importance_xgb.png")

# Random Forest feature importance
print("\nGenerating Random Forest feature importance plot...")
rf_importances = model_rf.feature_importances_
rf_indices = np.argsort(rf_importances)[::-1]

plt.figure(figsize=(10, 6))
plt.title('Random Forest Feature Importances', fontsize=14, fontweight='bold')
plt.bar(range(len(rf_importances)), rf_importances[rf_indices])
plt.xticks(range(len(rf_importances)), [feature_names[i] for i in rf_indices], rotation=45, ha='right')
plt.xlabel('Features')
plt.ylabel('Importance')
plt.tight_layout()
plt.savefig('feature_importance_rf.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: feature_importance_rf.png")

# Logistic Regression coefficients
print("\nLogistic Regression Coefficient Magnitudes:")
lr_coefs = model_lr.named_steps['classifier'].coef_[0]
lr_coef_abs = np.abs(lr_coefs)
lr_indices = np.argsort(lr_coef_abs)[::-1]

for idx in lr_indices:
    print(f"  {feature_names[idx]:25s}: {lr_coef_abs[idx]:8.4f} (raw: {lr_coefs[idx]:8.4f})")

# ============================================================================
# 6. SAVE MODELS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 6: SAVING TRAINED MODELS")
print("=" * 80)

joblib.dump(model_xgb, 'model_xgb.joblib')
print("✓ Saved: model_xgb.joblib")

joblib.dump(model_rf, 'model_rf.joblib')
print("✓ Saved: model_rf.joblib")

joblib.dump(model_lr, 'model_lr.joblib')
print("✓ Saved: model_lr.joblib")

# ============================================================================
# 7. FINAL SUMMARY TABLE
# ============================================================================

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

print("=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)
