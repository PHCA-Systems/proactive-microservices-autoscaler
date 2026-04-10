# GKE Training Results

## Overview

This document contains all training results for SLA violation prediction models trained on GKE (Google Kubernetes Engine) data from the Sock Shop microservices application.

**Models Trained**: XGBoost, Random Forest, Logistic Regression  
**Training Date**: April 9, 2026  
**SLA Threshold**: 35.68ms (P75 of front-end p95 under constant load, 50 users)

---

## Dataset Summary

### Separated Dataset (25 runs across 4 patterns)
| Pattern | Runs | Total Rows | Violations | Rate |
|---------|------|------------|------------|------|
| constant | 4 | 973 | 48 | 4.9% |
| ramp | 7 | 1,463 | 190 | 13.0% |
| spike | 7 | 1,449 | 152 | 10.5% |
| step | 7 | 1,435 | 200 | 13.9% |
| **TOTAL** | **25** | **5,320** | **590** | **11.1%** |

**Note**: Runs 5-7 for ramp/spike/step were initially unlabeled and were properly labeled using lookahead window methodology.

### Mixed Dataset (4-hour continuous run)
- **Total rows**: 3,570
- **Violations**: 475 (13.3%)
- **Duration**: ~4 hours
- **Pattern**: Mixed workload (all patterns combined)

---

## Experiment 1: Separated Dataset - Standard 80/20 Split

Stratified random split. SMOTE applied to training set only (50/50 balance).  
Train: 4,256 rows → 7,568 after SMOTE. Test: 1,064 rows (untouched).

| Model | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|-------|----------|-------------|-----------|-------|---------|
| XGBoost | 0.8750 | 0.4641 | 0.8220 | 0.5933 | 0.9492 |
| Random Forest | 0.9117 | 0.5723 | 0.8051 | 0.6690 | 0.9589 |
| Logistic Regression | 0.8647 | 0.4343 | 0.7288 | 0.5443 | 0.8919 |

**Confusion Matrices**:
- XGBoost: TN=834, FP=112, FN=21, TP=97
- Random Forest: TN=875, FP=71, FN=23, TP=95
- Logistic Regression: TN=834, FP=112, FN=32, TP=86

---

## Experiment 2: Separated Dataset - Cross-Pattern Leave-One-Out

Train on 3 patterns, test on held-out 4th. Repeated for all 4 combinations.

### XGBoost

| Hold-out | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|----------|----------|-------------|-----------|-------|---------|
| constant | 0.7749 | 0.1798 | 1.0000 | 0.3048 | 0.9547 |
| ramp | 0.8503 | 0.4589 | 0.8526 | 0.5967 | 0.9379 |
| spike | 0.7909 | 0.2691 | 0.5789 | 0.3674 | 0.8286 |
| step | 0.8983 | 0.5985 | 0.8200 | 0.6920 | 0.9372 |
| **MEAN** | **0.8286** | **0.3766** | **0.8129** | **0.4902** | **0.9146** |
| STD | 0.0491 | 0.1630 | 0.1512 | 0.1593 | 0.0501 |

### Random Forest

| Hold-out | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|----------|----------|-------------|-----------|-------|---------|
| constant | 0.7996 | 0.1925 | 0.9583 | 0.3206 | 0.9518 |
| ramp | 0.9064 | 0.6008 | 0.8316 | 0.6976 | 0.9518 |
| spike | 0.8744 | 0.4279 | 0.5855 | 0.4944 | 0.8870 |
| step | 0.9331 | 0.7766 | 0.7300 | 0.7526 | 0.9295 |
| **MEAN** | **0.8784** | **0.4995** | **0.7763** | **0.5663** | **0.9300** |
| STD | 0.0500 | 0.2159 | 0.1367 | 0.1714 | 0.0265 |

### Logistic Regression

| Hold-out | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|----------|----------|-------------|-----------|-------|---------|
| constant | 0.7657 | 0.1484 | 0.7917 | 0.2500 | 0.8770 |
| ramp | 0.8681 | 0.4942 | 0.6737 | 0.5702 | 0.8782 |
| spike | 0.9089 | 0.5543 | 0.6711 | 0.6071 | 0.8986 |
| step | 0.8641 | 0.5080 | 0.7900 | 0.6184 | 0.9094 |
| **MEAN** | **0.8517** | **0.4262** | **0.7316** | **0.5114** | **0.8908** |
| STD | 0.0527 | 0.1619 | 0.0592 | 0.1520 | 0.0137 |

---

## Experiment 3: Mixed Dataset - Standard 80/20 Split

Stratified random split. SMOTE applied to training set only (50/50 balance).  
Train: 2,856 rows → 4,952 after SMOTE. Test: 714 rows (untouched).

| Model | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|-------|----------|-------------|-----------|-------|---------|
| XGBoost | 0.8754 | 0.5183 | 0.8947 | 0.6564 | 0.9805 |
| **Random Forest** | **0.9468** | **0.7280** | **0.9579** | **0.8273** | **0.9917** |
| Logistic Regression | 0.9286 | 0.6618 | 0.9474 | 0.7792 | 0.9819 |

**Confusion Matrices**:
- XGBoost: TN=540, FP=79, FN=10, TP=85
- Random Forest: TN=585, FP=34, FN=4, TP=91
- Logistic Regression: TN=573, FP=46, FN=5, TP=90

---

## Key Observations

### 1. Mixed dataset outperforms separated dataset
Random Forest on mixed data achieves 94.7% accuracy and 95.8% recall, compared to 91.2% accuracy and 80.5% recall on separated data. The continuous 4-hour run better captures pattern transitions and sustained load behavior.

### 2. Spike generalization improved with proper labeling
After properly labeling runs 5-7 (which were initially all 0s), spike recall improved:
- XGBoost: 0.58 recall when spike is held out
- Random Forest: 0.59 recall when spike is held out

This is a significant improvement over initial unlabeled data where spike was the hardest pattern to generalize.

### 3. Random Forest excels on mixed patterns
On the mixed dataset, Random Forest outperforms XGBoost across all metrics:
- Accuracy: 94.7% vs 87.5%
- Recall: 95.8% vs 89.5%
- Precision: 72.8% vs 51.8%
- F1: 0.83 vs 0.66
- ROC-AUC: 0.99 vs 0.98

### 4. Cross-pattern generalization is strong for ramp and step
Both XGBoost and Random Forest generalize well when held-out pattern is ramp (ROC-AUC ~0.95) or step (ROC-AUC ~0.93). This demonstrates the models learn features that transfer across sustained and stepped load profiles.

### 5. Constant hold-out produces low precision, high recall
When trained on ramp+spike+step and tested on constant, precision is low (0.18-0.19) but recall is near-perfect (0.96-1.00). The model over-predicts violations on comfortable load because it was trained predominantly on stressed conditions.

---

## Deployment Recommendation

### Production Model: Random Forest (Mixed Dataset)

**Model Location**: `models_mixed_standard/model_rf.joblib`

**Expected Performance**:
- Accuracy: 94.7%
- Recall: 95.8% (detects 96% of violations)
- Precision: 72.8% (73% of alerts are true violations)
- F1 Score: 0.83
- ROC-AUC: 0.99

**Rationale**:
1. Highest recall - critical for autoscaling (missed violations hurt customers)
2. Best overall metrics across all experiments
3. Trained on realistic 4-hour mixed patterns
4. Robust to pattern transitions
5. Acceptable false alarm rate (27%)

**Alternative**: XGBoost on mixed dataset if lower false alarm rate is critical (51.8% precision vs 72.8%, but 89.5% recall vs 95.8%).

---

## Files and Artifacts

### Datasets
- `gke_separated_dataset.csv` - 5,320 rows, 590 violations
- `gke_mixed_dataset.csv` - 3,570 rows, 475 violations

### Trained Models
- `models_separated_standard/` - 3 models (XGBoost, RF, LR)
- `models_separated_cross_pattern/` - 12 models (3 models × 4 folds)
- `models_mixed_standard/` - 3 models (XGBoost, RF, LR)

### Results
- `results_separated_standard.json` - Standard split metrics
- `results_separated_cross_pattern.json` - Cross-pattern metrics
- `results_mixed_standard.json` - Mixed dataset metrics

### Visualizations
- `feature_importance_xgb_separated.png`
- `feature_importance_rf_separated.png`
- `feature_importance_xgb_mixed.png`
- `feature_importance_rf_mixed.png`

---

## Training Scripts

To retrain models:

1. **Prepare data**: `python prepare_data.py`
2. **Train on separated (standard)**: `python train_standard.py`
3. **Train on separated (cross-pattern)**: `python train_cross_pattern.py`

Note: Mixed dataset training uses the same `train_standard.py` script with `gke_mixed_dataset.csv` as input.

---

**Status**: ✅ Training Complete  
**Recommended for Production**: Random Forest (Mixed Dataset)  
**Model File**: `models_mixed_standard/model_rf.joblib`
