# Quick Start: Model Retraining with One-Hot Encoded Service

## TL;DR

Train all 3 models with one-hot encoded service feature on GKE Mixed 4-hour dataset.

## One-Command Execution

### Windows
```bash
cd kafka-structured/ML-Models/gke
run_onehot_training.bat
```

### Linux/Mac
```bash
cd kafka-structured/ML-Models/gke
python train_with_onehot_service.py
```

## What Happens

1. Loads `gke_mixed_dataset.csv`
2. One-hot encodes service feature (1 feature → 4 features)
3. Trains XGBoost, Random Forest, Logistic Regression
4. Saves models to `models_mixed_onehot/`
5. Saves results to `results_mixed_onehot.json`
6. Generates feature importance plots

## Compare Results

```bash
python compare_onehot_vs_standard.py
```

Compares:
- Standard (service as integer)
- One-hot (service encoded) ← **NEW**
- No service (excluded)

## Check Results

### Models
```
models_mixed_onehot/
├── model_xgb.joblib
├── model_rf.joblib
└── model_lr.joblib
```

### Metrics
```
results_mixed_onehot.json
```

### Plots
```
feature_importance_xgb_mixed_onehot.png
feature_importance_rf_mixed_onehot.png
```

### Comparison
```
comparison_service_encoding.csv
```

## Expected Runtime

- Training: ~5-15 minutes (depends on hardware)
- Comparison: <1 minute

## Prerequisites

```bash
pip install -r requirements.txt
```

## Need Help?

- Detailed docs: `RETRAINING_ONEHOT.md`
- Summary: `RETRAINING_SUMMARY.md`
- Script: `train_with_onehot_service.py`

## Key Metrics to Check

After training, look at `results_mixed_onehot.json`:

```json
{
  "XGBoost": {
    "accuracy": 0.XXXX,
    "precision_1": 0.XXXX,
    "recall_1": 0.XXXX,
    "f1_1": 0.XXXX,
    "roc_auc": 0.XXXX
  },
  "RandomForest": { ... },
  "LogisticRegression": { ... }
}
```

Focus on:
- **F1-Score (f1_1)**: Balance of precision and recall
- **ROC-AUC (roc_auc)**: Overall discrimination ability
- **Recall (recall_1)**: How many violations were caught

## Troubleshooting

**Error: No module named 'pandas'**
```bash
pip install -r requirements.txt
```

**Error: File not found**
```bash
# Make sure you're in the right directory
cd kafka-structured/ML-Models/gke
ls gke_mixed_dataset.csv
```

**Want to see progress?**
The script prints detailed progress to console. Watch for:
- Data loading
- One-hot encoding
- Training progress
- Evaluation results

---

**Ready to go!** Just run the command above. 🚀
