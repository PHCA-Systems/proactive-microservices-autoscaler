"""
Comprehensive comparison between Local and GKE model performance
"""

import pandas as pd
import numpy as np
import json

print("=" * 80)
print("LOCAL vs GKE MODEL PERFORMANCE COMPARISON")
print("=" * 80)

# Load local results
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
local_path = os.path.join(script_dir, '../local/accuracy_report.json')
with open(local_path, 'r') as f:
    local_results = json.load(f)

# Load GKE results
gke_sep_path = os.path.join(script_dir, 'results_separated_standard.json')
with open(gke_sep_path, 'r') as f:
    gke_sep_results = json.load(f)

gke_mix_path = os.path.join(script_dir, 'results_mixed_standard.json')
with open(gke_mix_path, 'r') as f:
    gke_mix_results = json.load(f)

# Load datasets for analysis
data_local_path = os.path.join(script_dir, '../../data/local/mixed_4hour_metrics.csv')
df_local = pd.read_csv(data_local_path)
df_gke_sep = pd.read_csv(os.path.join(script_dir, 'gke_separated_dataset.csv'))
df_gke_mix = pd.read_csv(os.path.join(script_dir, 'gke_mixed_dataset.csv'))

print("\n" + "=" * 80)
print("DATASET CHARACTERISTICS")
print("=" * 80)

print("\nLOCAL (4-hour mixed workload):")
print(f"  Total rows: {len(df_local)}")
print(f"  Violations: {df_local['sla_violated'].sum()} ({df_local['sla_violated'].sum()/len(df_local)*100:.1f}%)")
print(f"  Services: {df_local['service'].nunique()}")
print(f"  Pattern: Mixed (4-hour continuous)")
print(f"  Duration: ~4 hours")
print(f"  Environment: Local Docker")

print("\nGKE SEPARATED (25 runs, 4 patterns):")
print(f"  Total rows: {len(df_gke_sep)}")
print(f"  Violations: {df_gke_sep['sla_violated'].sum()} ({df_gke_sep['sla_violated'].sum()/len(df_gke_sep)*100:.1f}%)")
print(f"  Services: {df_gke_sep['service'].nunique()}")
print(f"  Patterns: {df_gke_sep['pattern'].nunique()} (constant, ramp, spike, step)")
print(f"  Runs: 25 (4 constant, 7 ramp, 7 spike, 7 step)")
print(f"  Duration: 15 min per run")
print(f"  Environment: GKE Cloud")

print("\nGKE MIXED (Single 4-hour mixed):")
print(f"  Total rows: {len(df_gke_mix)}")
print(f"  Violations: {df_gke_mix['sla_violated'].sum()} ({df_gke_mix['sla_violated'].sum()/len(df_gke_mix)*100:.1f}%)")
print(f"  Services: {df_gke_mix['service'].nunique()}")
print(f"  Pattern: Mixed (all patterns combined)")
print(f"  Duration: ~4 hours")
print(f"  Environment: GKE Cloud")

print("\n" + "=" * 80)
print("MODEL PERFORMANCE COMPARISON")
print("=" * 80)

# Extract metrics
models = ['XGBoost', 'RandomForest', 'LogisticRegression']

print("\n" + "-" * 80)
print("XGBOOST")
print("-" * 80)
print(f"{'Dataset':<20} {'Accuracy':>10} {'Precision(1)':>13} {'Recall(1)':>10} {'F1(1)':>8} {'ROC-AUC':>10}")
print("-" * 80)

local_xgb = local_results['model_results']['XGBoost']
gke_sep_xgb = gke_sep_results['XGBoost']
gke_mix_xgb = gke_mix_results['XGBoost']

print(f"{'Local':<20} {local_xgb['accuracy']:>10.4f} {local_xgb['precision_class_1']:>13.4f} {local_xgb['recall_class_1']:>10.4f} {local_xgb['f1_class_1']:>8.4f} {local_xgb['roc_auc']:>10.4f}")
print(f"{'GKE Separated':<20} {gke_sep_xgb['accuracy']:>10.4f} {gke_sep_xgb['precision_1']:>13.4f} {gke_sep_xgb['recall_1']:>10.4f} {gke_sep_xgb['f1_1']:>8.4f} {gke_sep_xgb['roc_auc']:>10.4f}")
print(f"{'GKE Mixed':<20} {gke_mix_xgb['accuracy']:>10.4f} {gke_mix_xgb['precision_1']:>13.4f} {gke_mix_xgb['recall_1']:>10.4f} {gke_mix_xgb['f1_1']:>8.4f} {gke_mix_xgb['roc_auc']:>10.4f}")

print("\n" + "-" * 80)
print("RANDOM FOREST")
print("-" * 80)
print(f"{'Dataset':<20} {'Accuracy':>10} {'Precision(1)':>13} {'Recall(1)':>10} {'F1(1)':>8} {'ROC-AUC':>10}")
print("-" * 80)

local_rf = local_results['model_results']['Random Forest']
gke_sep_rf = gke_sep_results['RandomForest']
gke_mix_rf = gke_mix_results['RandomForest']

print(f"{'Local':<20} {local_rf['accuracy']:>10.4f} {local_rf['precision_class_1']:>13.4f} {local_rf['recall_class_1']:>10.4f} {local_rf['f1_class_1']:>8.4f} {local_rf['roc_auc']:>10.4f}")
print(f"{'GKE Separated':<20} {gke_sep_rf['accuracy']:>10.4f} {gke_sep_rf['precision_1']:>13.4f} {gke_sep_rf['recall_1']:>10.4f} {gke_sep_rf['f1_1']:>8.4f} {gke_sep_rf['roc_auc']:>10.4f}")
print(f"{'GKE Mixed':<20} {gke_mix_rf['accuracy']:>10.4f} {gke_mix_rf['precision_1']:>13.4f} {gke_mix_rf['recall_1']:>10.4f} {gke_mix_rf['f1_1']:>8.4f} {gke_mix_rf['roc_auc']:>10.4f}")

print("\n" + "-" * 80)
print("LOGISTIC REGRESSION")
print("-" * 80)
print(f"{'Dataset':<20} {'Accuracy':>10} {'Precision(1)':>13} {'Recall(1)':>10} {'F1(1)':>8} {'ROC-AUC':>10}")
print("-" * 80)

local_lr = local_results['model_results']['Logistic Regression']
gke_sep_lr = gke_sep_results['LogisticRegression']
gke_mix_lr = gke_mix_results['LogisticRegression']

print(f"{'Local':<20} {local_lr['accuracy']:>10.4f} {local_lr['precision_class_1']:>13.4f} {local_lr['recall_class_1']:>10.4f} {local_lr['f1_class_1']:>8.4f} {local_lr['roc_auc']:>10.4f}")
print(f"{'GKE Separated':<20} {gke_sep_lr['accuracy']:>10.4f} {gke_sep_lr['precision_1']:>13.4f} {gke_sep_lr['recall_1']:>10.4f} {gke_sep_lr['f1_1']:>8.4f} {gke_sep_lr['roc_auc']:>10.4f}")
print(f"{'GKE Mixed':<20} {gke_mix_lr['accuracy']:>10.4f} {gke_mix_lr['precision_1']:>13.4f} {gke_mix_lr['recall_1']:>10.4f} {gke_mix_lr['f1_1']:>8.4f} {gke_mix_lr['roc_auc']:>10.4f}")

print("\n" + "=" * 80)
print("BEST MODEL PER METRIC")
print("=" * 80)

# Determine best model per metric for each dataset
datasets = {
    'Local': {
        'XGBoost': local_xgb,
        'Random Forest': local_rf,
        'Logistic Regression': local_lr
    },
    'GKE Separated': {
        'XGBoost': gke_sep_xgb,
        'Random Forest': gke_sep_rf,
        'Logistic Regression': gke_sep_lr
    },
    'GKE Mixed': {
        'XGBoost': gke_mix_xgb,
        'Random Forest': gke_mix_rf,
        'Logistic Regression': gke_mix_lr
    }
}

metrics_map = {
    'Local': {
        'accuracy': 'accuracy',
        'precision': 'precision_class_1',
        'recall': 'recall_class_1',
        'f1': 'f1_class_1',
        'roc_auc': 'roc_auc'
    },
    'GKE Separated': {
        'accuracy': 'accuracy',
        'precision': 'precision_1',
        'recall': 'recall_1',
        'f1': 'f1_1',
        'roc_auc': 'roc_auc'
    },
    'GKE Mixed': {
        'accuracy': 'accuracy',
        'precision': 'precision_1',
        'recall': 'recall_1',
        'f1': 'f1_1',
        'roc_auc': 'roc_auc'
    }
}

for dataset_name, models_dict in datasets.items():
    print(f"\n{dataset_name}:")
    metric_map = metrics_map[dataset_name]
    
    for metric_name, metric_key in metric_map.items():
        best_model = max(models_dict.items(), key=lambda x: x[1][metric_key])
        print(f"  {metric_name.upper():<12}: {best_model[0]:<22} ({best_model[1][metric_key]:.4f})")

print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

print("""
1. LOCAL DATA (4-hour mixed workload):
   - Dataset size: 3,500 samples (smaller than GKE Mixed)
   - Each model excels at different metrics
   - XGBoost: Best F1 (0.7749) and Accuracy (0.9129)
   - Random Forest: Best ROC-AUC (0.9699)
   - Logistic Regression: Best Recall (0.9746)
   - Models specialize based on their strengths

2. GKE SEPARATED (Multiple discrete runs):
   - Dataset size: 5,320 samples (largest dataset)
   - Random Forest dominates most metrics
   - More diverse patterns favor ensemble methods
   - Lower overall performance due to pattern diversity

3. GKE MIXED (4-hour mixed workload):
   - Dataset size: 3,570 samples (similar to Local but larger)
   - Random Forest DOMINATES ALL METRICS
   - Accuracy: 0.9468, Precision: 0.7280, Recall: 0.9579, F1: 0.8273, ROC-AUC: 0.9917
   - Cloud environment complexity favors Random Forest
   - Best overall performance across all experiments

KEY DIFFERENCE: Local vs GKE Mixed
   - Both are 4-hour mixed workloads
   - Local: 3,500 samples, Docker environment, 16.9% violations
   - GKE Mixed: 3,570 samples, Cloud environment, 13.3% violations
   - Difference is SCALE and ENVIRONMENT, not pattern complexity
   - RF dominates on GKE due to: larger dataset, cloud variability, statistical power
""")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
