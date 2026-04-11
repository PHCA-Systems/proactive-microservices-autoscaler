# Paper Final Updates - No Service Feature Models

## Key Change

Replaced all model results with the **experiment_no_service** results - models trained on GKE mixed dataset WITHOUT the service identity feature.

## Updated Model Performance (Section 5.2)

### GKE Mixed Dataset (No Service Feature)
| Model | Precision(1) | Recall(1) | F1(1) | ROC-AUC |
|-------|--------------|-----------|-------|---------|
| XGBoost | 0.535 | 0.884 | 0.667 | 0.980 |
| Random Forest | 0.750 | 0.916 | 0.825 | 0.991 |
| Logistic Regression | 0.987 | 0.811 | 0.890 | 0.967 |

**Key Finding:** Random Forest achieves best balance (75.0% precision, 91.6% recall, 99.1% ROC-AUC)

## Updated Local vs GKE Comparison (Section 5.3)

### XGBoost
- Precision: 68.0% local → 53.5% GKE (-14.5%)
- Recall: 88.1% local → 88.4% GKE (+0.3%)
- ROC-AUC: 96.2% local → 98.0% GKE (+1.8%)

### Random Forest
- Precision: 64.9% local → 75.0% GKE (+10.1%)
- Recall: 92.4% local → 91.6% GKE (-0.8%)
- ROC-AUC: 97.0% local → 99.1% GKE (+2.1%)

### Logistic Regression
- Precision: 62.2% local → 98.7% GKE (+36.5%)
- Recall: 97.5% local → 81.1% GKE (-16.4%)
- ROC-AUC: 94.6% local → 96.7% GKE (+2.1%)

**Key Finding:** Logistic Regression shifts from high-recall/low-precision to high-precision/low-recall on GKE

## Updated Ensemble Performance (Section 5.5)

- **Recall:** 93.7% (catches 89 of 95 violations)
- **Precision:** 76.3%
- **False Negative Rate:** 6.3% (6 missed violations)
- **Vote Distribution:**
  - 68 unanimous (all 3 models agreed)
  - 18 majority (2 models agreed)
  - 3 single-model triggers

## Feature Space Changes

### OLD (11 dimensions):
- Throughput: request_rate_rps
- Reliability: error_rate_pct
- Latency: p50, p95, p99
- Resources: cpu_usage_pct, memory_usage_mb
- Delta: delta_rps, delta_p95_latency_ms, delta_cpu_usage_pct
- **Service: service_encoded (0-6)**

### NEW (10 dimensions):
- Throughput: request_rate_rps
- Reliability: error_rate_pct
- Latency: p50, p95, p99
- Resources: cpu_usage_pct, memory_usage_mb
- Delta: delta_rps, delta_p95_latency_ms, delta_cpu_usage_pct
- **Service feature REMOVED**

## Rationale for No Service Feature

Added explanation in Section 4.1:
> "Service identity is excluded from the feature space. This design choice reflects the operational goal of building a service-agnostic autoscaler that can generalize across all microservices without requiring service-specific tuning or configuration."

## Test Set Size Correction

- **OLD:** 623 samples (20% of 3,115)
- **NEW:** 714 samples (actual test set size from results_no_service.json)

## Sections Updated

1. **Section 4.1** - Feature Vector Design
   - Changed from 11 to 10 dimensions
   - Added rationale for excluding service feature
   - Removed service encoding mapping

2. **Section 4.3** - Dataset Characteristics
   - Updated service heterogeneity discussion to reflect no service feature
   - Clarified that models learn service-agnostic patterns

3. **Section 5.1** - Model Selection and Training
   - Added explicit mention of 10-dimensional feature vector
   - Added service-agnostic design goal

4. **Section 5.2** - Model Performance Results
   - Updated Table 1 with no-service results
   - Changed best performer from XGBoost to Random Forest
   - Updated test set size to 714 samples

5. **Section 5.3** - Local vs GKE Comparison
   - Updated Table 2 with no-service comparison
   - Rewrote analysis focusing on Logistic Regression's precision shift
   - Added discussion of Random Forest's consistency

6. **Section 5.4** - Feature Importance Analysis
   - Removed specific importance values (not in results file)
   - Added discussion of service-agnostic pattern learning

7. **Section 5.5** - Ensemble Voting Analysis
   - Updated ensemble performance metrics
   - Changed from 11-dimensional to 10-dimensional feature space reference

8. **Section 3.2** - ML Inference Services
   - Removed service name encoding logic
   - Simplified preprocessing pipeline description

## Data Source

All metrics sourced from:
`kafka-structured/ML-Models/gke/experiment_no_service/results_no_service.json`

Specifically using the `GKE_Mixed` section:
```json
{
  "GKE_Mixed": {
    "XGBoost": {...},
    "RandomForest": {...},
    "LogisticRegression": {...}
  }
}
```

## Verification Checklist

- [x] All model performance metrics updated to no-service results
- [x] Feature vector changed from 11 to 10 dimensions
- [x] Service encoding logic removed from preprocessing
- [x] Test set size corrected to 714 samples
- [x] Ensemble performance recalculated
- [x] Local vs GKE comparison updated
- [x] Feature importance discussion updated
- [x] Rationale for no service feature added
- [x] All references to service-specific patterns updated
- [x] Best performing model changed from XGBoost to Random Forest

## Key Narrative Changes

1. **Service-Agnostic Design:** Paper now emphasizes building a generalizable autoscaler that works across all services without service-specific tuning

2. **Random Forest as Best Performer:** Random Forest (99.1% ROC-AUC, 91.6% recall) now outperforms XGBoost, providing best balance of precision and recall

3. **Logistic Regression Behavior:** LR shows interesting environment-specific behavior - conservative on GKE (high precision) vs aggressive on local (high recall)

4. **Ensemble Strength:** Ensemble achieves 93.7% recall, demonstrating that majority voting compensates for individual model weaknesses

## Paper Status

**Complete:** All sections updated with no-service experiment results
**Focus:** Service-agnostic autoscaling with 10-dimensional feature space
**Ready for:** Final review and submission
