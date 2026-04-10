# Experiment Overview: Training Without Service Feature

## The Problem We Discovered

During analysis of feature importance, we found that XGBoost assigns very high importance to the `service` feature, especially on GKE data. Investigation revealed why:

### Violation Rates by Service

**GKE Mixed Dataset:**
```
Service 0 (catalogue):  0.0% violations  ← Never violates
Service 1 (carts):     54.1% violations  ← High violation rate
Service 2 (front-end): 39.0% violations  ← High violation rate
Service 3 (orders):     0.0% violations  ← Never violates
Service 4 (payment):    0.0% violations  ← Never violates
Service 5 (shipping):   0.0% violations  ← Never violates
Service 6 (user):       0.0% violations  ← Never violates
```

**Local Dataset:**
```
catalogue:   0.4% violations
carts:       0.6% violations
front-end:  64.2% violations  ← High violation rate
orders:     52.8% violations  ← High violation rate
payment:     0.0% violations
shipping:    0.4% violations
user:        0.0% violations
```

## Why This Is a Problem

The service feature acts as a **strong proxy for the target variable**. The model learns:
- "If service == carts or front-end → predict violation"
- "Otherwise → predict no violation"

This is almost a perfect predictor, which:
1. **Masks other features**: Latency, CPU, memory become less important
2. **May indicate data issues**: Why do only 2 services violate SLAs?
3. **Limits generalization**: Model won't work if service characteristics change

## Three Possible Explanations

### 1. Service-Specific SLA Thresholds (Most Likely)
- Front-end and orders/carts are user-facing services
- They have stricter SLA requirements (35.68ms may be too strict for them)
- Other services are backend services with more relaxed SLAs
- **Solution**: Use service-specific thresholds

### 2. Workload Characteristics
- Front-end and orders/carts handle more complex operations
- They naturally have higher latency
- The 35.68ms threshold is appropriate, but these services struggle to meet it
- **Solution**: Keep service feature, it's genuinely predictive

### 3. Data Collection Issue
- Something wrong with how violations were labeled
- Service feature shouldn't be this predictive
- **Solution**: Re-examine labeling logic

## This Experiment Tests

**Hypothesis**: If we remove the service feature, can the model still predict violations using only metrics (latency, CPU, memory, etc.)?

### Scenario A: Performance Drops Significantly (>10%)
- **Interpretation**: Service is genuinely predictive
- **Action**: Keep service feature, it's valuable information
- **Implication**: Different services have different SLA requirements

### Scenario B: Performance Remains Similar (<5% drop)
- **Interpretation**: Service was acting as a shortcut
- **Action**: Model can learn from metrics alone
- **Implication**: The underlying patterns are in the metrics

### Scenario C: Performance Drops Moderately (5-10%)
- **Interpretation**: Service helps but isn't critical
- **Action**: Decide based on deployment constraints
- **Implication**: Trade-off between accuracy and generalization

## What We're Training

### Datasets (3 total)
1. **GKE Separated** - 5,320 rows, 25 runs, 4 patterns
2. **GKE Mixed** - 3,570 rows, 4-hour continuous
3. **Local** - 3,500 rows, 4-hour continuous

### Models (3 total)
1. **XGBoost** - Gradient boosting
2. **Random Forest** - Ensemble of trees
3. **Logistic Regression** - Linear model

### Features (10 total, service removed)
1. request_rate_rps
2. error_rate_pct
3. p50_latency_ms
4. p95_latency_ms ← Should become most important
5. p99_latency_ms
6. cpu_usage_pct
7. memory_usage_mb
8. delta_rps
9. delta_p95_latency_ms
10. delta_cpu_usage_pct

## Expected Outcomes

### Feature Importance Changes
- **p95_latency_ms** should become most important (it's the SLA threshold)
- **cpu_usage_pct** and **memory_usage_mb** should gain importance
- **delta_*** features should show trend importance

### Performance Changes
- **Best case**: <5% drop in accuracy/F1
- **Acceptable**: 5-10% drop
- **Problematic**: >10% drop

### Model Ranking
- Will Random Forest still dominate on GKE Mixed?
- Will XGBoost perform better without its "shortcut"?

## How to Interpret Results

### If p95_latency_ms becomes most important:
✅ Good! The model is learning the right patterns.
✅ SLA violations are driven by latency, as expected.

### If no clear feature dominates:
⚠️ Concerning. May indicate weak signal in the data.
⚠️ Model might be struggling to find patterns.

### If performance is acceptable:
✅ We can deploy without service feature.
✅ Model generalizes better across services.

### If performance drops significantly:
⚠️ Service feature is critical.
⚠️ Consider service-specific models or thresholds.

## Next Steps After Experiment

1. **Compare Results**
   - Run `compare_with_without_service.py`
   - Analyze performance changes
   - Check feature importance plots

2. **Make Decision**
   - Keep service feature?
   - Remove service feature?
   - Use service-specific thresholds?

3. **Document Findings**
   - Update thesis with insights
   - Explain why service is/isn't important
   - Justify final model choice

## Files Generated

### Results
- `results_no_service.json` - All metrics
- `COMPARISON.md` - With vs without analysis

### Models (9 total)
- `models/model_xgb_gke_separated.joblib`
- `models/model_rf_gke_separated.joblib`
- `models/model_lr_gke_separated.joblib`
- `models/model_xgb_gke_mixed.joblib`
- `models/model_rf_gke_mixed.joblib`
- `models/model_lr_gke_mixed.joblib`
- `models/model_xgb_local.joblib`
- `models/model_rf_local.joblib`
- `models/model_lr_local.joblib`

### Plots (6 total)
- Feature importance for XGBoost and RF on each dataset

---

**Ready to run?**
```bash
cd kafka-structured/ML-Models/gke/experiment_no_service
python train_no_service.py
```

Or on Windows:
```cmd
run_experiment.bat
```
