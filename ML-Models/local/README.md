# SLA Violation Prediction - ML Training Pipeline

Complete machine learning pipeline for predicting SLA violations in microservices during load ramp-up scenarios.

## 📊 Dataset

- **File**: `mixed_4hour_metrics.csv`
- **Samples**: 3,500 rows (4-hour monitoring data)
- **Features**: 11 features after preprocessing
- **Target**: `sla_violated` (binary: 0 or 1)
- **Class Distribution**: 16.91% positive class (592 violations, 2,908 normal)
- **Services**: 7 microservices (orders, front-end, catalogue, carts, payment, shipping, user)

## 🏗️ Project Structure

```
ML-Training/
├── config.py                      # Configuration and hyperparameters
├── preprocessing.py               # Data loading and preprocessing
├── smote_balancing.py            # SMOTE class balancing
├── model_training.py             # Model training logic
├── model_evaluation.py           # Evaluation metrics
├── feature_importance.py         # Feature importance analysis
├── model_persistence.py          # Model saving with parameters
├── accuracy_report.py            # Comprehensive reporting
├── main.py                       # Main pipeline orchestrator
├── inference_example.py          # Example inference script
├── requirements.txt              # Python dependencies
│
├── models/                       # Trained models (organized by type)
│   ├── xgboost/
│   │   ├── model.joblib         # Trained XGBoost model
│   │   ├── parameters.json      # Model hyperparameters
│   │   └── metrics.json         # Performance metrics
│   ├── random_forest/
│   │   ├── model.joblib
│   │   ├── parameters.json
│   │   └── metrics.json
│   └── logistic_regression/
│       ├── model.joblib
│       ├── parameters.json
│       └── metrics.json
│
├── feature_importance_xgb.png    # XGBoost feature importance plot
├── feature_importance_rf.png     # Random Forest feature importance plot
├── accuracy_report.json          # Machine-readable accuracy report
└── accuracy_report.txt           # Human-readable accuracy report
```

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Training

Run the complete training pipeline:

```bash
python main.py
```

This will:
1. Load and preprocess data
2. Split into train/test (80/20)
3. Apply SMOTE to training data only
4. Train 3 models (XGBoost, Random Forest, Logistic Regression)
5. Evaluate on test set
6. Generate feature importance plots
7. Save models with parameters to separate folders
8. Generate comprehensive accuracy reports

### Inference

Use trained models for predictions:

```bash
python inference_example.py
```

## 📈 Model Performance

### Summary Comparison

| Model | Accuracy | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|-------|----------|--------------|-----------|-------|---------|
| **XGBoost** | **0.9129** | 0.6863 | 0.8898 | 0.7749 | 0.9621 |
| **Random Forest** | 0.9014 | 0.6450 | 0.9237 | 0.7596 | **0.9699** |
| **Logistic Regression** | 0.8957 | 0.6216 | **0.9746** | 0.7591 | 0.9465 |

### Key Findings

- **Best Overall Accuracy**: XGBoost (91.29%)
- **Best Recall for Violations**: Logistic Regression (97.46% - only 3 missed violations out of 118)
- **Best ROC-AUC**: Random Forest (0.9699)

### Violation Detection Performance

| Model | Total Violations | Detected | Missed | Detection Rate |
|-------|-----------------|----------|--------|----------------|
| XGBoost | 118 | 105 | 13 | 89.0% |
| Random Forest | 118 | 109 | 9 | 92.4% |
| Logistic Regression | 118 | 115 | 3 | **97.5%** |

## 🎯 Model Selection Guide

Choose the right model for your use case:

- **Use Logistic Regression** if minimizing missed violations is critical (highest recall)
- **Use Random Forest** for best overall discrimination capability (highest ROC-AUC)
- **Use XGBoost** for highest overall accuracy and balanced performance

## 🔧 Configuration

All hyperparameters are centralized in `config.py`:

### XGBoost Parameters
```python
XGB_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.1,
    'scale_pos_weight': 4.91  # Calculated from class imbalance
}
```

### Random Forest Parameters
```python
RF_PARAMS = {
    'n_estimators': 200,
    'max_depth': 8,
    'class_weight': 'balanced'
}
```

### Logistic Regression Parameters
```python
LR_PARAMS = {
    'class_weight': 'balanced',
    'max_iter': 1000
}
```

## 📊 Feature Importance

Top features across models:

1. **p95_latency_ms** - 95th percentile latency (strongest predictor)
2. **p50_latency_ms** - Median latency
3. **cpu_usage_pct** - CPU utilization
4. **memory_usage_mb** - Memory consumption
5. **p99_latency_ms** - 99th percentile latency

## 🔄 Data Preprocessing

1. **Timestamp Removal**: Dropped for model training
2. **Service Encoding**: Fixed mapping (deterministic for inference)
   - catalogue=0, carts=1, front-end=2, orders=3, payment=4, shipping=5, user=6
3. **Missing Values**: NaN and inf filled with 0 (common in delta_* columns)
4. **Train/Test Split**: 80/20 stratified split (random_state=42)
5. **SMOTE**: Applied only to training data (50/50 balance)

### ⚠️ Important: Test Set Integrity

The test set is kept completely untouched from SMOTE to ensure:
- Unbiased performance estimates
- Valid thesis conclusions
- No data leakage
- Realistic production performance expectations

## 💾 Model Files

Each model folder contains:

1. **model.joblib**: Serialized trained model
2. **parameters.json**: Hyperparameters and service mapping
3. **metrics.json**: Performance metrics on test set

### Loading a Model

```python
import joblib
import json

# Load model
model = joblib.load('models/xgboost/model.joblib')

# Load parameters
with open('models/xgboost/parameters.json', 'r') as f:
    params = json.load(f)

# Load metrics
with open('models/xgboost/metrics.json', 'r') as f:
    metrics = json.load(f)
```

## 📝 Inference Example

```python
from inference_example import load_model_with_config, predict_sla_violation

# Load model
model, params, metrics = load_model_with_config('xgboost')

# Prepare data
data = {
    'service': 'orders',
    'request_rate_rps': 150.5,
    'error_rate_pct': 2.3,
    'p50_latency_ms': 45.2,
    'p95_latency_ms': 120.5,
    'p99_latency_ms': 180.3,
    'cpu_usage_pct': 75.2,
    'memory_usage_mb': 512.8,
    'delta_rps': 25.3,
    'delta_p95_latency_ms': 15.2,
    'delta_cpu_usage_pct': 10.5
}

# Predict
prediction, probability = predict_sla_violation(
    model, data, params['service_mapping']
)

print(f"Prediction: {prediction}")
print(f"Violation probability: {probability[1]:.2%}")
```

## 📄 Reports

### accuracy_report.txt
Human-readable comprehensive report with:
- Dataset information
- Training configuration
- Model comparison table
- Detailed metrics per model
- Confusion matrices
- Recommendations

### accuracy_report.json
Machine-readable JSON format for:
- Automated processing
- Dashboard integration
- API responses
- Monitoring systems

## 🔬 Methodology

1. **Class Imbalance Handling**: SMOTE oversampling (training only)
2. **Evaluation Metric Priority**: Recall for class 1 (violations)
3. **Cross-validation**: Stratified train/test split
4. **Feature Scaling**: StandardScaler for Logistic Regression only
5. **Random State**: 42 (reproducibility)

## 📦 Dependencies

- pandas >= 2.0.0
- numpy >= 1.24.0
- scikit-learn >= 1.3.0
- imbalanced-learn >= 0.11.0
- xgboost >= 2.0.0
- matplotlib >= 3.7.0
- joblib >= 1.3.0

## 🎓 Use Case

This pipeline is designed for:
- SLA violation prediction in microservices
- Load testing and capacity planning
- Proactive alerting systems
- Performance monitoring
- Thesis/research on ML for SRE

## 📧 Notes

- All models are production-ready and saved with their configurations
- Service mapping is deterministic for consistent inference
- Test set performance represents realistic production expectations
- Recall is prioritized over precision (missed violations are costly)

---

**Training Complete** ✅ All models trained, evaluated, and saved with comprehensive documentation.
