# Model Retraining with One-Hot Encoded Service Feature

## Overview

This document describes the retraining of all 3 models (XGBoost, Random Forest, Logistic Regression) with one-hot encoded service features on the GKE Mixed 4-hour dataset.

## Objective

Retrain models with improved feature engineering:
- **Dataset**: GKE Mixed 4-hour workload (`gke_mixed_dataset.csv`)
- **Feature Engineering**: One-hot encode the `service` feature instead of using it as an integer
- **Models**: XGBoost, Random Forest, Logistic Regression
- **Evaluation**: Comprehensive metrics matching previous training attempts

## Why One-Hot Encoding?

### Problem with Integer Encoding
When the service feature is encoded as integers (0, 1, 2, 3), machine learning models may interpret these as having an ordinal relationship:
- Service 3 > Service 2 > Service 1 > Service 0
- This implies a false ordering that doesn't exist in reality

### Benefits of One-Hot Encoding
- **No False Ordering**: Each service is represented as a separate binary feature
- **Better Representation**: Models can learn independent relationships for each service
- **Standard Practice**: One-hot encoding is the standard approach for categorical features
- **Feature Importance**: Can see which specific services are most predictive

## Implementation

### Files Created

1. **`train_with_onehot_service.py`**
   - Main training script
   - Loads GKE mixed dataset
   - Applies one-hot encoding to service feature
   - Trains all 3 models
   - Produces evaluation metrics and feature importance plots

2. **`run_onehot_training.bat`**
   - Batch script to execute training
   - Easy one-click execution

3. **`compare_onehot_vs_standard.py`**
   - Compares performance across encoding strategies:
     - Standard (service as integer)
     - One-hot (service encoded)
     - No service feature
   - Generates comparison CSV

4. **`RETRAINING_ONEHOT.md`** (this file)
   - Documentation of the retraining process

### Feature Engineering Details

**Original Features (10):**
- request_rate_rps
- error_rate_pct
- p50_latency_ms
- p95_latency_ms
- p99_latency_ms
- cpu_usage_pct
- memory_usage_mb
- delta_rps
- delta_p95_latency_ms
- delta_cpu_usage_pct

**Service Feature Transformation:**
- Original: `service` (integer: 0, 1, 2, 3)
- One-Hot Encoded: `service_0`, `service_1`, `service_2`, `service_3` (4 binary features)

**Total Features After One-Hot Encoding: 14**

## How to Run

### Prerequisites
```bash
pip install -r requirements.txt
```

Required packages:
- pandas >= 1.5.0
- numpy >= 1.23.0
- scikit-learn >= 1.2.0
- xgboost >= 1.7.0
- imbalanced-learn >= 0.10.0
- matplotlib >= 3.6.0
- joblib >= 1.2.0

### Training

**Option 1: Using batch script (Windows)**
```bash
cd kafka-structured/ML-Models/gke
run_onehot_training.bat
```

**Option 2: Direct Python execution**
```bash
cd kafka-structured/ML-Models/gke
python train_with_onehot_service.py
```

### Comparison

After training, compare with other encoding strategies:
```bash
python compare_onehot_vs_standard.py
```

## Outputs

### Models
Saved to `models_mixed_onehot/`:
- `model_xgb.joblib` - XGBoost model
- `model_rf.joblib` - Random Forest model
- `model_lr.joblib` - Logistic Regression model

### Results
- `results_mixed_onehot.json` - Detailed evaluation metrics for all models

### Visualizations
- `feature_importance_xgb_mixed_onehot.png` - XGBoost feature importance
- `feature_importance_rf_mixed_onehot.png` - Random Forest feature importance

### Comparison
- `comparison_service_encoding.csv` - Performance comparison across encoding strategies

## Evaluation Metrics

For each model, the following metrics are computed:

### Classification Metrics
- **Accuracy**: Overall correctness
- **Precision (Class 1)**: Of predicted violations, how many were correct
- **Recall (Class 1)**: Of actual violations, how many were detected
- **F1-Score (Class 1)**: Harmonic mean of precision and recall
- **ROC-AUC**: Area under the ROC curve

### Confusion Matrix
- **True Negatives (TN)**: Correctly predicted no violation
- **False Positives (FP)**: Incorrectly predicted violation
- **False Negatives (FN)**: Missed violations
- **True Positives (TP)**: Correctly predicted violation

## Expected Results

### Performance Expectations

**One-Hot Encoding vs Integer Encoding:**
- Should provide better or equal performance
- More interpretable feature importance
- No false ordinal relationships

**One-Hot Encoding vs No Service:**
- Should significantly outperform if service is predictive
- May show which specific services are most prone to violations

### Feature Importance Insights

With one-hot encoding, you can identify:
1. Which specific services are most predictive of violations
2. Whether service matters at all (compare importance of service_* features)
3. How service importance compares to other metrics (CPU, latency, etc.)

## Comparison with Previous Training

### Training Configurations Compared

| Configuration | Service Feature | Dataset | Purpose |
|--------------|----------------|---------|---------|
| Standard | Integer (0-3) | GKE Mixed | Baseline |
| One-Hot | Binary (4 features) | GKE Mixed | **This training** |
| No Service | Excluded | GKE Mixed | Control experiment |

### Key Questions Answered

1. **Does one-hot encoding improve performance?**
   - Compare F1-Score and ROC-AUC between Standard and One-Hot

2. **Is service feature important?**
   - Compare One-Hot vs No Service performance
   - Check feature importance plots

3. **Which services are most problematic?**
   - Look at importance of individual service_* features

## Next Steps

After reviewing results:

1. **If One-Hot Performs Better:**
   - Use one-hot encoded models for deployment
   - Update inference pipeline to apply same encoding

2. **If Service Features Are Important:**
   - Investigate why certain services have more violations
   - Consider service-specific autoscaling policies

3. **If Service Features Are Not Important:**
   - Consider using simpler model without service
   - Focus optimization on other features (CPU, latency, etc.)

## Troubleshooting

### Common Issues

**Issue: ModuleNotFoundError**
```bash
# Solution: Install requirements
pip install -r requirements.txt
```

**Issue: FileNotFoundError for dataset**
```bash
# Solution: Ensure you're in the correct directory
cd kafka-structured/ML-Models/gke
# Verify dataset exists
ls gke_mixed_dataset.csv
```

**Issue: Memory error during training**
```bash
# Solution: Reduce SMOTE sampling or use smaller dataset
# Edit train_with_onehot_service.py and adjust sampling_strategy
```

## References

- Original training script: `train_standard.py`
- No service experiment: `experiment_no_service/train_no_service.py`
- Dataset preparation: `prepare_data.py`
- GKE mixed dataset: `gke_mixed_dataset.csv`

## Contact

For questions or issues with this retraining:
1. Check the comparison results in `comparison_service_encoding.csv`
2. Review feature importance plots
3. Compare with previous training results in `results_mixed_standard.json`
