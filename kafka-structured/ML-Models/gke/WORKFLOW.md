# Retraining Workflow

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GKE Mixed 4-Hour Dataset                     │
│                    (gke_mixed_dataset.csv)                      │
│                                                                 │
│  Columns: service, request_rate_rps, error_rate_pct,          │
│           p50/p95/p99_latency_ms, cpu_usage_pct,              │
│           memory_usage_mb, delta_*, sla_violated, pattern      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Engineering                          │
│                                                                 │
│  1. Drop 'pattern' column (not available at inference)         │
│  2. One-hot encode 'service' feature:                          │
│     service (0,1,2,3) → service_0, service_1,                  │
│                         service_2, service_3                    │
│  3. Handle NaN/inf values                                      │
│                                                                 │
│  Result: 14 features (10 original + 4 service features)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Train/Test Split (80/20)                     │
│                                                                 │
│  Stratified split to maintain class distribution               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SMOTE (Class Balancing)                      │
│                                                                 │
│  Balance training set to 50/50 (violation/no violation)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Model Training                               │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │    XGBoost      │  │  Random Forest  │  │   Logistic      ││
│  │                 │  │                 │  │   Regression    ││
│  │  n_estimators:  │  │  n_estimators:  │  │                 ││
│  │  200            │  │  200            │  │  class_weight:  ││
│  │  max_depth: 6   │  │  max_depth: 8   │  │  balanced       ││
│  │  scale_pos_wt   │  │  class_weight:  │  │  max_iter: 1000 ││
│  │                 │  │  balanced       │  │                 ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Evaluation on Test Set                       │
│                                                                 │
│  Metrics per model:                                            │
│  • Accuracy                                                    │
│  • Precision (Class 0 & 1)                                     │
│  • Recall (Class 0 & 1)                                        │
│  • F1-Score (Class 0 & 1)                                      │
│  • ROC-AUC                                                     │
│  • Confusion Matrix (TP, TN, FP, FN)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Importance Analysis                  │
│                                                                 │
│  • XGBoost feature importances                                 │
│  • Random Forest feature importances                           │
│  • Visualizations saved as PNG                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Save Outputs                                 │
│                                                                 │
│  Models:                                                       │
│  • models_mixed_onehot/model_xgb.joblib                        │
│  • models_mixed_onehot/model_rf.joblib                         │
│  • models_mixed_onehot/model_lr.joblib                         │
│                                                                 │
│  Results:                                                      │
│  • results_mixed_onehot.json                                   │
│                                                                 │
│  Visualizations:                                               │
│  • feature_importance_xgb_mixed_onehot.png                     │
│  • feature_importance_rf_mixed_onehot.png                      │
└─────────────────────────────────────────────────────────────────┘
```

## Comparison Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Results Files                           │
│                                                                 │
│  1. results_mixed_standard.json (service as integer)           │
│  2. results_mixed_onehot.json (service one-hot encoded)        │
│  3. experiment_no_service/results_no_service.json              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Compare Metrics                              │
│                                                                 │
│  For each model (XGBoost, RF, LR):                             │
│  • Compare accuracy across strategies                          │
│  • Compare precision, recall, F1 for Class 1                   │
│  • Compare ROC-AUC                                             │
│  • Identify best performing strategy                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Generate Comparison Report                   │
│                                                                 │
│  • Console output with comparison tables                       │
│  • comparison_service_encoding.csv                             │
│  • Best strategy recommendations                               │
└─────────────────────────────────────────────────────────────────┘
```

## File Dependencies

```
train_with_onehot_service.py
    │
    ├─ Reads: gke_mixed_dataset.csv
    │
    └─ Writes:
        ├─ models_mixed_onehot/model_xgb.joblib
        ├─ models_mixed_onehot/model_rf.joblib
        ├─ models_mixed_onehot/model_lr.joblib
        ├─ results_mixed_onehot.json
        ├─ feature_importance_xgb_mixed_onehot.png
        └─ feature_importance_rf_mixed_onehot.png

compare_onehot_vs_standard.py
    │
    ├─ Reads:
    │   ├─ results_mixed_standard.json
    │   ├─ results_mixed_onehot.json
    │   └─ experiment_no_service/results_no_service.json
    │
    └─ Writes:
        └─ comparison_service_encoding.csv
```

## Execution Flow

### Step 1: Training
```bash
python train_with_onehot_service.py
```

**Duration**: ~5-15 minutes

**Console Output**:
1. Data loading progress
2. One-hot encoding details
3. Train/test split info
4. SMOTE balancing stats
5. Model training progress
6. Evaluation metrics per model
7. Feature importance rankings
8. File save confirmations

### Step 2: Comparison
```bash
python compare_onehot_vs_standard.py
```

**Duration**: <1 minute

**Console Output**:
1. Strategy loading status
2. Detailed comparison tables
3. Best performing strategies
4. Recommendations
5. CSV save confirmation

## Key Decision Points

```
                    ┌─────────────────────┐
                    │  Review Results     │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │ One-Hot Performs      │    │ One-Hot Performs      │
    │ Better?               │    │ Worse?                │
    └───────────┬───────────┘    └───────────┬───────────┘
                │                             │
                ▼                             ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │ Use one-hot models    │    │ Investigate why       │
    │ for deployment        │    │ • Check feature imp   │
    │                       │    │ • Review data quality │
    └───────────────────────┘    └───────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Check service         │
    │ feature importance    │
    └───────────┬───────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌─────────────┐    ┌─────────────────┐
│ Important?  │    │ Not important?  │
└──────┬──────┘    └────────┬────────┘
       │                    │
       ▼                    ▼
┌─────────────┐    ┌─────────────────┐
│ Investigate │    │ Consider model  │
│ service-    │    │ without service │
│ specific    │    │ for simplicity  │
│ issues      │    │                 │
└─────────────┘    └─────────────────┘
```

## Success Criteria

✅ **Training Successful** if:
- All 3 models train without errors
- Models saved to `models_mixed_onehot/`
- Results JSON contains all metrics
- Feature importance plots generated

✅ **Comparison Successful** if:
- All result files loaded
- Comparison CSV generated
- Console shows comparison tables

✅ **Results Valid** if:
- ROC-AUC > 0.5 (better than random)
- F1-Score > 0.0 (model is learning)
- Confusion matrix shows TP > 0 (detecting violations)

## Troubleshooting Flow

```
Error Occurred?
    │
    ├─ ModuleNotFoundError
    │   └─ pip install -r requirements.txt
    │
    ├─ FileNotFoundError
    │   └─ Check you're in kafka-structured/ML-Models/gke/
    │
    ├─ MemoryError
    │   └─ Reduce SMOTE sampling_strategy
    │
    └─ ValueError (data issues)
        └─ Check dataset for NaN/inf values
```

---

**Ready to execute!** Follow the workflow above. 🚀
