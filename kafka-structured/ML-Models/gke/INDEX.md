# GKE Model Training - Document Index

## Start Here 🚀

**New to this analysis?** Read in this order:

1. **QUICK_SUMMARY.md** - One-page visual summary (5 min read)
2. **CORRECTED_ANALYSIS_SUMMARY.md** - What was wrong, what's correct (10 min read)
3. **COMPARISON_SUMMARY.md** - Detailed comparison (15 min read)
4. **RESULTS.md** - Complete training results (20 min read)

---

## Document Categories

### 📊 Quick Reference
- **QUICK_SUMMARY.md** - One-page visual summary with ASCII diagrams
- **README.md** - Project overview and quick start guide
- **DATASET_COMPARISON.md** - Dataset characteristics at a glance

### 🔍 Analysis Documents
- **CORRECTED_ANALYSIS_SUMMARY.md** - What was corrected and why
- **COMPARISON_SUMMARY.md** - Local vs GKE quick comparison
- **LOCAL_VS_GKE_ANALYSIS.md** - Full detailed analysis with theory
- **CORRECTIONS_MADE.md** - Audit trail of all corrections

### 📈 Results
- **RESULTS.md** - Complete training results and metrics
- **FINAL_RESULTS.md** - Detailed results with all experiments
- **results_separated_standard.json** - Raw metrics (separated dataset)
- **results_separated_cross_pattern.json** - Raw metrics (cross-pattern)
- **results_mixed_standard.json** - Raw metrics (mixed dataset)

### 🔧 Scripts
- **prepare_data.py** - Data loading and preprocessing
- **train_standard.py** - Standard 80/20 training
- **train_cross_pattern.py** - Cross-pattern validation
- **label_all_runs.py** - Apply SLA labels to separated runs
- **apply_sla_labels.py** - Apply SLA labels to mixed dataset
- **compare_local_vs_gke.py** - Compare Local vs GKE performance
- **analyze_datasets.py** - Detailed dataset analysis

### 📁 Data Files
- **gke_separated_dataset.csv** - 25 runs, 4 patterns, 5,320 rows
- **gke_mixed_dataset.csv** - 4-hour mixed, 3,570 rows

### 🤖 Model Files
- **models_separated_standard/** - Models trained on separated (80/20)
- **models_separated_cross_pattern/** - Cross-pattern models (4 folds)
- **models_mixed_standard/** - Models trained on mixed (80/20) ⭐ **RECOMMENDED**

---

## Key Questions Answered

### "Which model should I use in production?"
→ **QUICK_SUMMARY.md** or **README.md**

### "Why does Random Forest dominate on GKE?"
→ **CORRECTED_ANALYSIS_SUMMARY.md** or **QUICK_SUMMARY.md**

### "What's the difference between Local and GKE datasets?"
→ **DATASET_COMPARISON.md** or **COMPARISON_SUMMARY.md**

### "What were the training results?"
→ **RESULTS.md** or **FINAL_RESULTS.md**

### "What was corrected in the analysis?"
→ **CORRECTIONS_MADE.md** or **CORRECTED_ANALYSIS_SUMMARY.md**

### "How do I retrain the models?"
→ **README.md** (How to Retrain section)

### "What's the detailed theory behind RF dominance?"
→ **LOCAL_VS_GKE_ANALYSIS.md**

---

## Quick Facts

### Best Model
- **Random Forest** trained on GKE Mixed dataset
- 94.7% accuracy, 95.8% recall, 99.2% ROC-AUC
- File: `models_mixed_standard/model_rf.joblib`

### Key Finding
- Environment complexity (Docker vs Cloud) determines model performance
- Not dataset size (3,500 vs 3,570 is negligible)
- Not pattern complexity (both are mixed workloads)
- Cloud infrastructure favors ensemble methods

### Datasets
- **Local**: 3,500 samples, 4-hour mixed, Docker, 16.9% violations
- **GKE Mixed**: 3,570 samples, 4-hour mixed, Cloud, 13.3% violations
- Nearly identical in size and pattern type

### Performance
- **Local**: Each model excels at different metrics
- **GKE**: Random Forest dominates ALL metrics
- **Reason**: Cloud variability favors ensemble robustness

---

## Document Status

### ✅ Corrected Documents
- LOCAL_VS_GKE_ANALYSIS.md
- COMPARISON_SUMMARY.md
- compare_local_vs_gke.py
- README.md

### ✅ New Documents
- CORRECTED_ANALYSIS_SUMMARY.md
- DATASET_COMPARISON.md
- CORRECTIONS_MADE.md
- QUICK_SUMMARY.md
- INDEX.md (this file)

### ✅ Original Documents (Still Valid)
- RESULTS.md
- FINAL_RESULTS.md
- All training scripts
- All model files
- All JSON results

---

## For Thesis/Paper

### Key Sections to Reference
1. **QUICK_SUMMARY.md** - For visual summary in presentation
2. **LOCAL_VS_GKE_ANALYSIS.md** - For detailed methodology section
3. **RESULTS.md** - For results section
4. **DATASET_COMPARISON.md** - For dataset description

### Key Insight for Contribution
"We demonstrate that deployment environment complexity has a greater impact on model performance than dataset characteristics. Using nearly identical datasets (3,500 vs 3,570 samples, both 4-hour mixed workloads), we show that Random Forest dominates all metrics on distributed cloud infrastructure (GKE) while models specialize on consistent local infrastructure (Docker). This finding emphasizes the importance of training and evaluating ML models in environments that match production deployment."

### Tables to Include
- Dataset comparison (from DATASET_COMPARISON.md)
- Model performance comparison (from COMPARISON_SUMMARY.md)
- Performance changes Local→GKE (from CORRECTED_ANALYSIS_SUMMARY.md)

---

## Maintenance

### To Update Results
1. Run new experiments
2. Update `RESULTS.md` with new metrics
3. Update `README.md` if best model changes
4. Keep analysis documents as-is (they explain methodology)

### To Add New Analysis
1. Create new markdown file
2. Add to this INDEX.md
3. Link from README.md if important

---

**Last Updated**: 2026-04-09
**Status**: All corrections complete, analysis accurate
