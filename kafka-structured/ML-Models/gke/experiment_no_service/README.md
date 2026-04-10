# Experiment: Training Without Service Feature

## Motivation

Analysis revealed that the `service` feature has extremely high importance in XGBoost models, particularly on GKE data. Investigation showed that certain services have very high violation rates while others have almost none:

### GKE Mixed Dataset
- Service 1 (carts): 54.1% violations
- Service 2 (front-end): 39% violations
- All other services: 0% violations

### Local Dataset
- front-end: 64.2% violations
- orders: 52.8% violations
- All other services: <1% violations

This means the service feature acts as a strong proxy for the target variable, potentially masking the importance of other features.

## Experiment Goal

Train all three models (XGBoost, Random Forest, Logistic Regression) on all three datasets WITHOUT the service feature to:

1. See if other features become more important
2. Understand how much performance degrades without service
3. Determine if the model can learn from metrics alone
4. Compare feature importance across datasets when service is removed

## Features Used

Only 10 features (service removed):
1. request_rate_rps
2. error_rate_pct
3. p50_latency_ms
4. p95_latency_ms
5. p99_latency_ms
6. cpu_usage_pct
7. memory_usage_mb
8. delta_rps
9. delta_p95_latency_ms
10. delta_cpu_usage_pct

## Datasets Tested

1. **GKE Separated** - 5,320 rows, 25 runs across 4 patterns
2. **GKE Mixed** - 3,570 rows, 4-hour continuous mixed workload
3. **Local** - 3,500 rows, 4-hour continuous mixed workload

## How to Run

```bash
cd kafka-structured/ML-Models/gke/experiment_no_service
python train_no_service.py
```

## Expected Outputs

### Models
- `models/model_xgb_gke_separated.joblib`
- `models/model_rf_gke_separated.joblib`
- `models/model_lr_gke_separated.joblib`
- `models/model_xgb_gke_mixed.joblib`
- `models/model_rf_gke_mixed.joblib`
- `models/model_lr_gke_mixed.joblib`
- `models/model_xgb_local.joblib`
- `models/model_rf_local.joblib`
- `models/model_lr_local.joblib`

### Results
- `results_no_service.json` - Complete metrics for all models and datasets
- `COMPARISON.md` - Analysis comparing with-service vs without-service performance

### Feature Importance Plots
- `feature_importance_xgb_gke_separated.png`
- `feature_importance_rf_gke_separated.png`
- `feature_importance_xgb_gke_mixed.png`
- `feature_importance_rf_gke_mixed.png`
- `feature_importance_xgb_local.png`
- `feature_importance_rf_local.png`

## Questions to Answer

1. **Performance Impact**: How much does accuracy/recall/F1 drop without service?
2. **Feature Shift**: Which features become most important when service is removed?
3. **Model Comparison**: Do models rank differently without service?
4. **Dataset Differences**: Does the impact vary across Local vs GKE datasets?
5. **Practical Viability**: Can we deploy a model without service feature?

## Hypothesis

If performance drops significantly (>10% in key metrics), it confirms that service is genuinely predictive and should be kept. If performance remains similar, it suggests service was acting as a shortcut and the model can learn from metrics alone.

## Next Steps

After running this experiment:
1. Compare results with original models (with service)
2. Analyze which features gained importance
3. Decide whether to:
   - Keep service feature (if it's genuinely predictive)
   - Remove service feature (if performance is acceptable)
   - Use service-specific SLA thresholds (if service is a proxy for different SLA requirements)
