# Session Summary — GKE Data Collection & Model Training

## Context

This project builds an ML-based SLA violation predictor for Sock Shop microservices
running on GKE. A local version already existed (trained on a 4-hour mixed Docker run).
This session reproduced and extended that pipeline on real cloud infrastructure, collected
per-pattern experiment data, derived a cloud-appropriate SLA threshold, labeled the dataset,
trained and evaluated models, and ran an overnight batch to collect additional runs and a
4-hour mixed GKE dataset.

---

## Fixes Applied Before Experiments

### MongoDB driver causing high error rates
The metrics aggregator was using an incompatible MongoDB driver version, which caused the
carts and orders services to fail under any meaningful load. This manifested as 18-20%
aggregate error rates in the first experiment. After fixing the driver version, error rates
dropped below 1% and the checkout flow worked correctly.

### queue-master removed from collection
queue-master is a deprecated service in the Sock Shop benchmark. It was originally built
to spawn Docker containers for a Weave Scope demo and was never properly implemented as a
real microservice. Its Prometheus metrics endpoint returns nothing, so every collected row
showed cpu=0, mem=0, rps=0 across all 82 samples. It was removed from the default_services
list in metrics_collector.py so it no longer appears in any collected data.

### Early CSV split
The original sockshop_metrics.csv contained two separate experiments concatenated together
with a 14-minute gap between them — the high-error run (exp1) and the fixed run (exp2).
These were split into separate files. exp1 is kept in legacy/ for reference but is not
used for training. exp2 is the clean baseline.

### Locust duration bug
All load patterns use a LoadTestShape class that reads LOCUST_RUN_TIME_MINUTES from the
environment to determine how long to run. This variable was never being set when launching
Locust via SSH, so every experiment defaulted to 10 minutes regardless of the --run-time
flag passed on the command line. The --run-time flag controls Locust's overall timeout but
the shape class controls when it actually stops generating load — and the shape was always
stopping at 10 minutes. Fixed by explicitly setting LOCUST_RUN_TIME_MINUTES=15 in the SSH
command before launching Locust.

---

## Data Collection

### Infrastructure
- GKE cluster: sock-shop-cluster, us-central1-a, 3x e2-standard-4 nodes
- Prometheus: installed via Helm, 5s scrape interval, accessed via kubectl port-forward
- Locust: running on a GCE VM (locust-runner, e2-small), sending traffic to the front-end
  LoadBalancer external IP
- Metrics aggregator: running locally, polling Prometheus every 30 seconds, writing CSV

### Load patterns
Four patterns from the EuroSys'24 Erlang paper, each implemented as a Locust LoadTestShape:

| Pattern  | Description                          | User range     |
|----------|--------------------------------------|----------------|
| constant | Flat steady-state load               | 50 users       |
| ramp     | Gradual increase to peak, then down  | 10 to 150      |
| spike    | Low base load with sharp bursts      | 10 base, 100 peak |
| step     | Sudden jumps between load levels     | 50/200/100/300/50 |

### Per-experiment structure
Each run: 60s warmup (aggregator collects baseline with no load) + load duration + 60s
winddown (aggregator captures recovery). This gives clean before/after context around
each load event.

### Runs collected

| Pattern  | Runs | Rows/run | Notes                              |
|----------|------|----------|------------------------------------|
| constant | 4    | 238-245  | Used for SLA threshold derivation  |
| ramp     | 7    | 175-245  | run_1-4 earlier (10min), run_5-7 overnight (15min) |
| spike    | 7    | 175-245  | same split as ramp                 |
| step     | 7    | 175-245  | same split as step                 |
| mixed    | 1    | 3570     | 15-segment 4-hour run (overnight)  |

The difference in row counts between earlier and later runs is because the Locust duration
bug was fixed partway through collection. Runs 1-4 for ramp/spike/step have 10.5 minutes
of actual load; runs 5-7 have 15 minutes. Both are valid and labeled correctly.

### Mixed 4-hour run
Replicates the exact local experiment sequence: 15 segments totaling 240 minutes, with
the same pattern order and durations as the original run_experiment.py --gen4patterns.
One aggregator runs continuously for the full duration while Locust segments are launched
sequentially with 5-second gaps between them.

Sequence: ramp(15m) → constant(20m) → spike(10m) → step(30m) → ramp(25m) → constant(15m)
→ spike(5m) → step(20m) → ramp(10m) → constant(30m) → spike(15m) → step(10m) →
ramp(20m) → constant(10m) → spike(15m)

---

## SLA Threshold Derivation

No contractual SLA exists for Sock Shop, so the threshold was derived empirically using
the same methodology as the local dataset.

### Methodology
Run the system at comfortable load (constant pattern, 50 users). Observe the p95 latency
the front-end naturally produces under these conditions. Take the P75 of those observations
as the SLA threshold. This represents the upper bound of normal operating conditions —
25% of comfortable-load observations exceed it, capturing the tail of normal behavior
without being so tight that routine variance triggers violations.

Front-end p95 was chosen as the signal because front-end is the user-facing entry point
that every request passes through. It aggregates the effect of all downstream service
degradation into a single user-visible metric.

### Calculation
P75 of front-end p95 latency across 4 constant runs (loaded rows only, rps > 1):

| Run   | P75     |
|-------|---------|
| run_1 | 32.40ms |
| run_2 | 35.18ms |
| run_3 | 36.50ms |
| run_4 | 37.17ms |
| Mean  | 35.31ms |

Threshold used: **35.68ms** (computed from pooled constant data directly)

### Why different from local (9.86ms)
The local threshold was derived the same way — P25 of front-end p95 on the local dataset,
which happened to equal ~9.86ms. The difference reflects the latency gap between local
Docker networking (~5ms baseline) and GKE cloud networking (~30ms baseline). Same
methodology, different environment. The threshold is environment-specific by design.

### Validation
| Pattern  | % front-end loaded rows exceeding threshold |
|----------|---------------------------------------------|
| constant | 24.6%                                       |
| ramp     | 81.8%                                       |
| spike    | 54.5%                                       |
| step     | 88.6%                                       |

The threshold scales proportionally with load intensity, confirming it is a genuine
discriminator and not a trivially easy or trivially hard bar.

---

## Labeling

Labels are predictive: sla_violated=1 means "p95 latency will exceed the threshold in
the next 2 polls (60 seconds)." This is the same lookahead buffer logic used in the
local collect_metrics.py, applied post-hoc. Since the full dataset is available after
collection, the result is identical to what live labeling would have produced. The only
difference is the last 2 rows of each run, which are labeled 0 conservatively because
there is no future data to look ahead to.

| Dataset  | Total rows | Violations | Rate  |
|----------|------------|------------|-------|
| GKE all  | 3,115      | 377        | 12.1% |
| Local    | 3,500      | 592        | 16.9% |

The lower violation rate in GKE data is expected — the threshold is higher in absolute
terms (35.68ms vs 9.86ms), and the constant pattern (which has very few violations by
design) makes up a larger proportion of the GKE dataset.

---

## Model Training

### Experiment 1: Standard 80/20 split
Stratified random split. SMOTE applied to training set only (50/50 balance, sampling_strategy=1.0).
Test set left completely untouched. Same pipeline as local train_models.py.

| Model               | Precision(1) | Recall(1) | F1(1)  | ROC-AUC |
|---------------------|--------------|-----------|--------|---------|
| XGBoost             | 0.634        | 0.947     | 0.759  | 0.981   |
| Random Forest       | 0.613        | 0.907     | 0.731  | 0.975   |
| Logistic Regression | 0.378        | 0.787     | 0.511  | 0.902   |

XGBoost: 4 missed violations out of 75 in the test set. 41 false alarms out of 548.

### Experiment 2: Cross-pattern leave-one-out
Train on 3 patterns, test on the held-out 4th. Repeated for all 4 combinations.
This experiment directly validates the separate-pattern collection strategy by testing
whether models trained on some patterns generalize to unseen ones.

**XGBoost mean across 4 folds: Recall 0.756, ROC-AUC 0.925**

Key findings:
- Ramp and step generalize well (ROC-AUC ~0.95 when held out)
- Spike is the hardest pattern to generalize to — recall drops to 0.50 when held out,
  because spike bursts produce short sharp latency signatures that are qualitatively
  different from the sustained load in ramp/step/constant training data
- When constant is held out, the model over-predicts violations (high recall, low
  precision) because it was trained predominantly on stressed conditions and has not
  seen comfortable-load behavior

### Comparison to local results

| Model         | Metric       | Local | GKE   |
|---------------|--------------|-------|-------|
| XGBoost       | Precision(1) | 0.686 | 0.634 |
| XGBoost       | Recall(1)    | 0.890 | 0.947 |
| XGBoost       | ROC-AUC      | 0.962 | 0.981 |
| Random Forest | Precision(1) | 0.645 | 0.613 |
| Random Forest | Recall(1)    | 0.924 | 0.907 |
| Random Forest | ROC-AUC      | 0.970 | 0.975 |
| LR            | Precision(1) | 0.622 | 0.378 |
| LR            | Recall(1)    | 0.975 | 0.787 |
| LR            | ROC-AUC      | 0.946 | 0.902 |

XGBoost and Random Forest are comparable or slightly better on ROC-AUC. Precision dropped
slightly across all models, caused by the lower natural violation rate (12.1% vs 16.9%)
which means SMOTE generates more synthetic positives to reach 50/50, pushing the decision
boundary to be more liberal. Logistic Regression degraded significantly because it is a
linear model that struggles with the wider and more complex latency variance of cloud data.
LR is the baseline comparator in this work, not the deployment model.

---

## Folder Structure

```
kafka-structured/
  data/
    local/
      mixed_4hour_metrics.csv       # 4-hour mixed run on local Docker
      hour_ramp_metrics.csv         # 1-hour ramp run on local Docker
    gke/
      experiments/
        constant/run_1-4/metrics.csv
        ramp/run_1-7/metrics.csv
        spike/run_1-7/metrics.csv
        step/run_1-7/metrics.csv
      mixed/
        metrics.csv                 # 4-hour mixed run on GKE (3570 rows)
      legacy/
        sockshop_metrics_exp1.csv   # Pre-fix run (high error rate, not used)
        sockshop_metrics_exp2.csv   # First clean run after MongoDB fix

  ML-Models/
    local/                          # Original local training pipeline
      train_models.py
      preprocessing.py / config.py / smote_balancing.py / ...
      model_xgb.joblib / model_rf.joblib / model_lr.joblib
      accuracy_report.txt / .json
      feature_importance_xgb.png / feature_importance_rf.png
      models/
        xgboost/   random_forest/   logistic_regression/
          model.joblib / metrics.json / parameters.json
    gke/                            # GKE training pipeline
      prepare_data.py
      train_standard.py
      train_cross_pattern.py
      gke_combined.csv              # Merged labeled dataset (3115 rows)
      results_standard.json
      results_cross_pattern.json
      RESULTS.md
      feature_importance_xgb_gke.png / feature_importance_rf_gke.png
      models/
        standard/                   # model_xgb/rf/lr.joblib
        cross_pattern/              # model_<name>_holdout_<pattern>.joblib (12 files)

  scripts/
    run_all_experiments.ps1         # Per-pattern experiment runner
    run_overnight.ps1               # Overnight batch runner with GKE shutdown

  load-testing/                     # Locust files and load pattern configs
  metrics-collection/               # Local Prometheus collector (Docker)
  services/
    metrics-aggregator/             # GKE Prometheus collector (cloud)
    ml-inference/
    authoritative-scaler/
  microservices-demo/               # Sock Shop deployment manifests
  batch/                            # Windows batch scripts for local stack
```

---

## What's Next

- Apply SLA labeling to the mixed GKE dataset (mixed/metrics.csv) using the same
  35.68ms threshold and lookahead logic
- Retrain models including the new runs (run_5-7 for ramp/spike/step) and the mixed dataset
- Evaluate whether the additional data improves precision
- Hook the GKE-trained models into the inference service
- Write paper sections: data collection methodology, threshold derivation, experimental results
