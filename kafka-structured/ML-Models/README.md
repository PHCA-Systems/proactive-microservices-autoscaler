# ML Models Documentation

## Overview

This directory contains trained machine learning models for SLA violation prediction in the Sock Shop microservices benchmark. Models are trained on both local Docker and GKE cloud environments.

## Directory Structure

```
ML-Models/
├── gke/                          # GKE-trained models
│   ├── models/
│   │   ├── standard/             # 80/20 split models
│   │   └── cross_pattern/        # Leave-one-out cross-validation
│   ├── train_standard.py
│   ├── train_cross_pattern.py
│   ├── prepare_data.py
│   ├── gke_combined.csv          # Labeled dataset (3115 rows)
│   └── results_*.json
│
└── local/                        # Local Docker-trained models
    ├── models/
    │   ├── xgboost/
    │   ├── random_forest/
    │   └── logistic_regression/
    ├── train_models.py
    ├── preprocessing.py
    └── config.py
```

## Model Performance

### GKE Models (Standard 80/20 Split)

| Model | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|-------|--------------|-----------|-------|---------|
| XGBoost | 0.634 | 0.947 | 0.759 | 0.981 |
| Random Forest | 0.613 | 0.907 | 0.731 | 0.975 |
| Logistic Regression | 0.378 | 0.787 | 0.511 | 0.902 |

### Cross-Pattern Validation

XGBoost mean across 4 folds:
- **Recall**: 0.756
- **ROC-AUC**: 0.925

Key findings:
- Ramp and step patterns generalize well (ROC-AUC ~0.95)
- Spike is hardest to generalize (recall drops to 0.50 when held out)
- Constant pattern over-predicts when held out

### Local vs GKE Comparison

| Model | Metric | Local | GKE |
|-------|--------|-------|-----|
| XGBoost | Precision(1) | 0.686 | 0.634 |
| XGBoost | Recall(1) | 0.890 | 0.947 |
| XGBoost | ROC-AUC | 0.962 | 0.981 |

## Dataset Information

### GKE Dataset
- **Total rows**: 3,115
- **Violations**: 377 (12.1%)
- **SLA Threshold**: 35.68ms (p95 latency)
- **Runs**: 25 experiments + 1 mixed 4-hour run
- **Patterns**: constant, ramp, spike, step

### Local Dataset
- **Total rows**: 3,500
- **Violations**: 592 (16.9%)
- **SLA Threshold**: 9.86ms (p95 latency)

## Feature Engineering

### 11-Dimensional Feature Vector

**Throughput**:
- request_rate_rps

**Reliability**:
- error_rate_pct

**Latency**:
- p50_latency_ms
- p95_latency_ms
- p99_latency_ms

**Resources**:
- cpu_usage_pct
- memory_usage_mb

**Trajectory** (delta features):
- delta_rps
- delta_p95_latency_ms
- delta_cpu_usage_pct

**Service**:
- service identifier (0-6 encoding)

## Training Pipeline

### Standard Training (80/20 Split)

```bash
cd kafka-structured/ML-Models/gke
python prepare_data.py
python train_standard.py
```

### Cross-Pattern Validation

```bash
python train_cross_pattern.py
```

## Model Files

Each model directory contains:
- `model.joblib`: Trained scikit-learn model
- `parameters.json`: Hyperparameters and service mapping
- `metrics.json`: Performance metrics

## SLA Threshold Derivation

### Methodology
1. Run system at comfortable load (constant pattern, 50 users)
2. Observe p95 latency of front-end service
3. Take P75 of observations as SLA threshold
4. This represents upper bound of normal operating conditions

### GKE Threshold Calculation

P75 of front-end p95 latency across 4 constant runs:

| Run | P75 |
|-----|-----|
| run_1 | 32.40ms |
| run_2 | 35.18ms |
| run_3 | 36.50ms |
| run_4 | 37.17ms |
| **Mean** | **35.31ms** |

**Final Threshold**: 35.68ms

### Validation

| Pattern | % Rows Exceeding Threshold |
|---------|----------------------------|
| constant | 24.6% |
| ramp | 81.8% |
| spike | 54.5% |
| step | 88.6% |

## Labeling Logic

Labels are predictive with 60-second lookahead:
- `sla_violated=1`: p95 latency will exceed threshold in next 2 polls (60 seconds)
- `sla_violated=0`: No violation expected

This provides a 60-second warning window for proactive scaling.

## Usage in Production

The GKE standard models are deployed in the ML inference services:
- `services/ml-inference/xgboost/`
- `services/ml-inference/random-forest/`
- `services/ml-inference/logistic-regression/`

Each service:
1. Subscribes to Kafka `metrics` topic
2. Loads pre-trained model from `model.joblib`
3. Runs inference on incoming feature vectors
4. Publishes predictions to `model-votes` topic

## Retraining

To retrain models with new data:

1. Collect new metrics using metrics aggregator
2. Label data using `prepare_data.py`
3. Retrain using `train_standard.py`
4. Evaluate performance
5. Deploy new models to inference services

## References

- Scikit-learn: https://scikit-learn.org/
- XGBoost: https://xgboost.readthedocs.io/
- SMOTE: https://imbalanced-learn.org/
