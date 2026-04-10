# Instructions: Running the No-Service Experiment

## Quick Start

### Option 1: Windows Batch File
```cmd
cd kafka-structured\ML-Models\gke\experiment_no_service
run_experiment.bat
```

### Option 2: Direct Python
```bash
cd kafka-structured/ML-Models/gke/experiment_no_service
python train_no_service.py
```

### Option 3: With Virtual Environment
```bash
# If you have a venv
source /path/to/venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

cd kafka-structured/ML-Models/gke/experiment_no_service
python train_no_service.py
```

## Prerequisites

Ensure you have these packages installed:
```bash
pip install pandas numpy scikit-learn imbalanced-learn xgboost matplotlib joblib
```

Or use the requirements file from the local directory:
```bash
pip install -r ../../local/requirements.txt
```

## What Happens When You Run

The script will:

1. **Load 3 datasets**
   - GKE Separated (5,320 rows)
   - GKE Mixed (3,570 rows)
   - Local (3,500 rows)

2. **Remove service feature** from all datasets

3. **Train 9 models** (3 models × 3 datasets)
   - XGBoost
   - Random Forest
   - Logistic Regression

4. **Generate outputs**
   - JSON results file
   - 9 model files
   - 6 feature importance plots

**Expected runtime**: 5-10 minutes depending on your machine

## Checking Progress

The script prints detailed progress:
```
================================================================================
EXPERIMENT: TRAINING WITHOUT SERVICE FEATURE
================================================================================

Hypothesis: Service feature may be acting as a proxy for the target
Testing: How do models perform when forced to learn from metrics alone?

Features used (10 total):
   1. request_rate_rps
   2. error_rate_pct
   ...

================================================================================
TRAINING ON: GKE Separated
================================================================================

Dataset: 5320 rows, 10 features
Class distribution: 0=4730  1=590  (11.09% violations)

Train: 4256  Test: 1064
...
```

## After Training Completes

### 1. Check the Results File
```bash
cat results_no_service.json
```

Look for:
- Accuracy values
- Recall values (most important for catching violations)
- F1 scores

### 2. View Feature Importance Plots
Open these PNG files:
- `feature_importance_xgb_gke_mixed.png`
- `feature_importance_rf_gke_mixed.png`
- `feature_importance_xgb_local.png`
- `feature_importance_rf_local.png`
- etc.

**What to look for:**
- Is p95_latency_ms now the most important feature?
- Which features gained importance?
- Are the patterns similar across datasets?

### 3. Run the Comparison Script
```bash
python compare_with_without_service.py
```

This will show:
- Side-by-side comparison of WITH vs WITHOUT service
- Performance changes for each model
- Average impact across all datasets

## Interpreting Results

### Key Metrics to Check

1. **Accuracy**
   - How often is the model correct overall?
   - Target: >85% is good, >90% is excellent

2. **Recall (Class 1)**
   - How many violations did we catch?
   - Target: >80% is acceptable, >90% is excellent
   - This is the MOST IMPORTANT metric

3. **F1 Score (Class 1)**
   - Balance between precision and recall
   - Target: >0.70 is good, >0.80 is excellent

4. **ROC-AUC**
   - Overall discrimination ability
   - Target: >0.90 is good, >0.95 is excellent

### Performance Drop Guidelines

**< 5% drop**: Excellent! Service wasn't critical.
- Model can learn from metrics alone
- Safe to deploy without service feature
- Better generalization

**5-10% drop**: Acceptable. Service helps but isn't critical.
- Trade-off decision needed
- Consider deployment constraints
- May be worth the generalization benefit

**> 10% drop**: Significant. Service is important.
- Keep service feature in production model
- Service provides valuable information
- Consider service-specific thresholds

### Feature Importance Analysis

**Expected pattern (healthy):**
```
p95_latency_ms:        0.35  ← Highest (SLA threshold)
cpu_usage_pct:         0.15
memory_usage_mb:       0.12
delta_p95_latency_ms:  0.10
p99_latency_ms:        0.08
...
```

**Concerning pattern:**
```
request_rate_rps:      0.25  ← No clear leader
error_rate_pct:        0.18
cpu_usage_pct:         0.15
p95_latency_ms:        0.12  ← Should be higher
...
```

## Common Issues

### ModuleNotFoundError
```
ModuleNotFoundError: No module named 'sklearn'
```
**Solution**: Install requirements
```bash
pip install scikit-learn pandas numpy xgboost imbalanced-learn matplotlib joblib
```

### FileNotFoundError
```
FileNotFoundError: [Errno 2] No such file or directory: '../gke_mixed_dataset.csv'
```
**Solution**: Run from the correct directory
```bash
cd kafka-structured/ML-Models/gke/experiment_no_service
```

### Memory Error
```
MemoryError: Unable to allocate array
```
**Solution**: Close other applications or reduce dataset size in the script

## What to Do Next

### If Performance is Good (< 5% drop)

1. **Document findings**
   - Service feature was acting as a shortcut
   - Model can learn from metrics alone
   - Better generalization expected

2. **Consider deployment**
   - Use models without service feature
   - Simpler, more generalizable
   - Works across all services

3. **Update thesis**
   - Explain why service was removed
   - Show performance comparison
   - Justify decision

### If Performance Drops Significantly (> 10% drop)

1. **Keep service feature**
   - It's genuinely predictive
   - Provides valuable information
   - Worth the specificity

2. **Investigate why**
   - Are SLA thresholds service-specific?
   - Do services have different characteristics?
   - Should we use service-specific models?

3. **Consider alternatives**
   - Service-specific SLA thresholds
   - Separate models per service
   - Service-aware ensemble

## Questions to Answer

After running the experiment, answer these:

1. ✅ How much did performance drop without service?
2. ✅ Which feature became most important?
3. ✅ Does Random Forest still dominate on GKE Mixed?
4. ✅ Are the patterns consistent across datasets?
5. ✅ Is the performance acceptable for production?
6. ✅ Should we keep or remove the service feature?

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Verify all prerequisites are installed
3. Ensure you're in the correct directory
4. Check that all data files exist
5. Review the EXPERIMENT_OVERVIEW.md for context

---

**Ready? Let's run it!**
```bash
python train_no_service.py
```
