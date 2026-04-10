# Start Here: No-Service Feature Experiment

## What We Discovered

The `service` feature has extremely high importance in XGBoost models. Investigation revealed:

**GKE Mixed**: Only services 1 (carts) and 2 (front-end) have violations (54% and 39% respectively). All other services: 0%.

**Local**: Only front-end (64%) and orders (53%) have violations. All other services: <1%.

This means service is almost a perfect predictor of violations!

## The Question

Can the model predict SLA violations using only metrics (latency, CPU, memory) without the service feature?

## The Experiment

Train all 3 models (XGBoost, Random Forest, Logistic Regression) on all 3 datasets (GKE Separated, GKE Mixed, Local) WITHOUT the service feature.

## How to Run

**Quick start:**
```bash
cd kafka-structured/ML-Models/gke/experiment_no_service
python train_no_service.py
```

**Or on Windows:**
```cmd
run_experiment.bat
```

**Runtime**: 5-10 minutes

## What You'll Get

1. **results_no_service.json** - All metrics
2. **9 trained models** - One per dataset/model combination
3. **6 feature importance plots** - See which features matter now
4. **Comparison analysis** - Run `compare_with_without_service.py`

## What to Look For

### Performance Drop
- **< 5%**: Service wasn't critical, safe to remove
- **5-10%**: Acceptable trade-off
- **> 10%**: Service is important, keep it

### Feature Importance
- **p95_latency_ms** should become most important
- Check if patterns make sense
- Compare across datasets

## Files in This Directory

- **START_HERE.md** (this file) - Quick overview
- **EXPERIMENT_OVERVIEW.md** - Detailed explanation of the problem
- **INSTRUCTIONS.md** - Step-by-step guide
- **README.md** - Experiment goals and setup
- **train_no_service.py** - Main training script
- **compare_with_without_service.py** - Comparison script
- **run_experiment.bat** - Windows batch file

## Quick Decision Tree

```
Run experiment
    ↓
Check results
    ↓
Performance drop < 5%?
    ↓ YES                           ↓ NO
Remove service feature          Keep service feature
Better generalization          It's genuinely predictive
Simpler model                  Consider service-specific thresholds
```

## Next Steps

1. ✅ Run the experiment
2. ✅ Check results_no_service.json
3. ✅ View feature importance plots
4. ✅ Run compare_with_without_service.py
5. ✅ Make decision: keep or remove service?
6. ✅ Document findings in thesis

---

**Ready to start?**
```bash
python train_no_service.py
```

**Need more context?** Read EXPERIMENT_OVERVIEW.md

**Need detailed instructions?** Read INSTRUCTIONS.md
