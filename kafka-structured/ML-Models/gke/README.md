# GKE Model Training

This directory contains trained machine learning models for predicting SLA violations in the Sock Shop microservices application running on GKE.

## Quick Start

### View Results
- `QUICK_SUMMARY.md` - One-page visual summary ⭐ **START HERE**
- `CORRECTED_ANALYSIS_SUMMARY.md` - Why Random Forest dominates on GKE ⭐ **KEY INSIGHTS**
- `RESULTS.md` - Complete training results and model performance metrics
- `COMPARISON_SUMMARY.md` - Quick Local vs GKE comparison

### Use Trained Models
The recommended production model is:
```
models_mixed_standard/model_rf.joblib
```

Load it with:
```python
import joblib
model = joblib.load('models_mixed_standard/model_rf.joblib')
```

Expected performance: 94.7% accuracy, 95.8% recall, 0.992 ROC-AUC

## What's Here

### Data Files
- `gke_separated_dataset.csv` - 25 runs across 4 load patterns (5,320 rows)
- `gke_mixed_dataset.csv` - 4-hour continuous mixed workload (3,570 rows)

### Trained Models (18 total)
- `models_separated_standard/` - Models trained on separated patterns (80/20 split)
- `models_separated_cross_pattern/` - Models for cross-pattern evaluation (4 folds)
- `models_mixed_standard/` - Models trained on mixed workload (80/20 split) ⭐ **RECOMMENDED**

### Scripts
- `prepare_data.py` - Loads and preprocesses raw data
- `train_standard.py` - Trains models with 80/20 split
- `train_cross_pattern.py` - Trains models with leave-one-out cross-validation
- `label_all_runs.py` - Applies SLA violation labels to unlabeled runs
- `apply_sla_labels.py` - Labels the mixed dataset
- `compare_local_vs_gke.py` - Compares Local vs GKE performance
- `analyze_datasets.py` - Detailed dataset analysis

### Analysis Documents
- `RESULTS.md` - Complete training results ⭐
- `FINAL_RESULTS.md` - Detailed results with all experiments
- `CORRECTED_ANALYSIS_SUMMARY.md` - Corrected Local vs GKE analysis ⭐
- `LOCAL_VS_GKE_ANALYSIS.md` - Full detailed comparison
- `COMPARISON_SUMMARY.md` - Quick comparison summary
- `DATASET_COMPARISON.md` - Dataset characteristics
- `results_*.json` - Raw metrics in JSON format

## Training Summary

| Dataset | Best Model | Accuracy | Recall | F1 | ROC-AUC |
|---------|-----------|----------|--------|-----|---------|
| Separated | Random Forest | 91.2% | 80.5% | 0.67 | 0.96 |
| **Mixed** | **Random Forest** | **94.7%** | **95.8%** | **0.83** | **0.99** |

**Recommendation**: Use Random Forest trained on mixed dataset for production.

## Key Finding: Why Random Forest Dominates on GKE

**Question**: Why does Random Forest dominate all metrics on GKE, but on Local data each model excels at different metrics?

**Answer**: Environment complexity, not dataset characteristics.

### The Facts
- Local dataset: 3,500 samples, 4-hour mixed workload, Docker environment
- GKE Mixed dataset: 3,570 samples, 4-hour mixed workload, Cloud environment
- Datasets are nearly identical in size and pattern type (+2% difference)

### The Difference
- **Local (Docker)**: Consistent infrastructure, predictable resources → Models specialize
- **GKE (Cloud)**: Variable infrastructure, distributed nodes → Random Forest dominates

### Why Random Forest Wins on Cloud
1. **200 trees** handle infrastructure variability (different nodes, network conditions)
2. **Bagging** averages out environment-specific noise
3. **Ensemble robustness** prevents overfitting to specific scenarios
4. **Feature randomization** captures complex infrastructure interactions

### Performance Comparison

**Local (Docker)**:
- XGBoost: Best accuracy (91.3%) and F1 (0.775)
- Random Forest: Best ROC-AUC (0.970)
- Logistic Regression: Best recall (97.5%)
- Each model excels at different metrics ✅

**GKE (Cloud)**:
- Random Forest: Best at ALL metrics (94.7% accuracy, 95.8% recall, 0.992 ROC-AUC)
- One model dominates everything ✅

**Read `CORRECTED_ANALYSIS_SUMMARY.md` for full explanation.**

## How to Retrain

1. Ensure data is in `../../data/gke/experiments/` and `../../data/gke/mixed/`
2. Run: `python prepare_data.py`
3. Run: `python train_standard.py`
4. Check `RESULTS.md` for updated metrics

## Questions?

- See `CORRECTED_ANALYSIS_SUMMARY.md` for why RF dominates ⭐ **START HERE**
- See `COMPARISON_SUMMARY.md` for Local vs GKE quick comparison
- See `LOCAL_VS_GKE_ANALYSIS.md` for deep-dive analysis
- See `RESULTS.md` for detailed training results
- See `FINAL_RESULTS.md` for complete experiment documentation
- Model files are in `models_*/` directories
- Raw metrics are in `results_*.json` files
