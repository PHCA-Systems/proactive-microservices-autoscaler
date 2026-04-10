"""
Compare model performance WITH vs WITHOUT service feature
"""

import json
import os

print("=" * 80)
print("COMPARISON: WITH SERVICE vs WITHOUT SERVICE")
print("=" * 80)

# Load results
script_dir = os.path.dirname(__file__)
with_service = {
    'GKE_Separated': json.load(open(os.path.join(script_dir, '../results_separated_standard.json'))),
    'GKE_Mixed': json.load(open(os.path.join(script_dir, '../results_mixed_standard.json'))),
    'Local': json.load(open(os.path.join(script_dir, '../../local/accuracy_report.json')))['model_results']
}

without_service = json.load(open(os.path.join(script_dir, 'results_no_service.json')))

# Normalize model names
def normalize_model_name(name):
    mapping = {
        'XGBoost': 'XGBoost',
        'RandomForest': 'Random Forest',
        'Random Forest': 'Random Forest',
        'LogisticRegression': 'Logistic Regression',
        'Logistic Regression': 'Logistic Regression'
    }
    return mapping.get(name, name)

# Normalize metric names
def get_metric(results, model, metric, dataset):
    # Try both naming conventions
    model_variants = [model, normalize_model_name(model)]
    
    for model_name in model_variants:
        if model_name in results:
            if dataset == 'Local':
                # Local has different key names
                metric_map = {
                    'accuracy': 'accuracy',
                    'precision_1': 'precision_class_1',
                    'recall_1': 'recall_class_1',
                    'f1_1': 'f1_class_1',
                    'roc_auc': 'roc_auc'
                }
                return results[model_name].get(metric_map.get(metric, metric), 0)
            else:
                return results[model_name].get(metric, 0)
    
    # If not found, return 0
    return 0

# Compare each dataset
for dataset_name in ['GKE_Separated', 'GKE_Mixed', 'Local']:
    print(f"\n{'=' * 80}")
    print(f"{dataset_name}")
    print(f"{'=' * 80}")
    
    with_results = with_service[dataset_name]
    without_results = without_service[dataset_name]
    
    models = ['XGBoost', 'RandomForest', 'LogisticRegression']
    metrics = ['accuracy', 'precision_1', 'recall_1', 'f1_1', 'roc_auc']
    
    for model in models:
        print(f"\n{normalize_model_name(model)}")
        print("-" * 80)
        print(f"{'Metric':<15} {'With Service':>15} {'Without Service':>18} {'Change':>12} {'% Change':>12}")
        print("-" * 80)
        
        for metric in metrics:
            with_val = get_metric(with_results, model, metric, dataset_name)
            without_val = without_results[model].get(metric, 0)
            change = without_val - with_val
            pct_change = (change / with_val * 100) if with_val != 0 else 0
            
            metric_display = metric.replace('_', ' ').title()
            print(f"{metric_display:<15} {with_val:>15.4f} {without_val:>18.4f} {change:>12.4f} {pct_change:>11.1f}%")

# Summary: Average impact across all datasets
print("\n" + "=" * 80)
print("SUMMARY: AVERAGE IMPACT OF REMOVING SERVICE FEATURE")
print("=" * 80)

models = ['XGBoost', 'RandomForest', 'LogisticRegression']
metrics = ['accuracy', 'precision_1', 'recall_1', 'f1_1', 'roc_auc']

print(f"\n{'Model':<22} {'Metric':<15} {'Avg Change':>12} {'Avg % Change':>15}")
print("-" * 80)

for model in models:
    for metric in metrics:
        changes = []
        pct_changes = []
        
        for dataset_name in ['GKE_Separated', 'GKE_Mixed', 'Local']:
            with_val = get_metric(with_service[dataset_name], model, metric, dataset_name)
            without_val = without_service[dataset_name][model].get(metric, 0)
            change = without_val - with_val
            pct_change = (change / with_val * 100) if with_val != 0 else 0
            changes.append(change)
            pct_changes.append(pct_change)
        
        avg_change = sum(changes) / len(changes)
        avg_pct_change = sum(pct_changes) / len(pct_changes)
        
        metric_display = metric.replace('_', ' ').title()
        print(f"{normalize_model_name(model):<22} {metric_display:<15} {avg_change:>12.4f} {avg_pct_change:>14.1f}%")

# Key insights
print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

print("""
1. PERFORMANCE IMPACT:
   - Check if accuracy/F1 drops significantly (>10% = service is critical)
   - Check if recall drops (missed violations increase)
   - Compare across all three models

2. MODEL RANKING:
   - Does Random Forest still dominate on GKE Mixed?
   - Do models rank differently without service?

3. PRACTICAL IMPLICATIONS:
   - If performance is acceptable, service may be acting as a shortcut
   - If performance drops significantly, service is genuinely predictive
   - Consider service-specific SLA thresholds as alternative

4. FEATURE IMPORTANCE:
   - Check feature importance plots to see which features gained importance
   - p95_latency_ms should become more important if it's truly predictive
""")

print("\n" + "=" * 80)
print("COMPARISON COMPLETE")
print("=" * 80)
