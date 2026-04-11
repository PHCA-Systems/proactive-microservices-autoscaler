"""
Compare model performance:
- Standard (with service as integer)
- One-hot encoded service
- No service feature

This provides a comprehensive view of how different service feature
encodings affect model performance.
"""

import os
import json
import pandas as pd

OUTPUT_DIR = os.path.dirname(__file__)

# Load results
results_files = {
    'Mixed Standard (service as int)': 'results_mixed_standard.json',
    'Mixed One-Hot (service encoded)': 'results_mixed_onehot.json',
    'No Service Feature': 'experiment_no_service/results_no_service.json'
}

print("=" * 80)
print("COMPARISON: SERVICE FEATURE ENCODING STRATEGIES")
print("=" * 80)
print("\nDataset: GKE Mixed 4-hour")
print("\nStrategies compared:")
print("  1. Standard: Service as integer (0, 1, 2, 3)")
print("  2. One-Hot: Service one-hot encoded (4 binary features)")
print("  3. No Service: Service feature excluded entirely")
print("\n" + "=" * 80)

all_results = {}
for strategy_name, results_file in results_files.items():
    results_path = os.path.join(OUTPUT_DIR, results_file)
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            data = json.load(f)
            # Handle nested structure for no_service results
            if 'GKE_Mixed' in data:
                all_results[strategy_name] = data['GKE_Mixed']
            else:
                all_results[strategy_name] = data
        print(f"✓ Loaded: {strategy_name}")
    else:
        print(f"✗ Not found: {strategy_name} ({results_file})")

if not all_results:
    print("\nNo results files found. Please run training scripts first.")
    exit(1)

# Create comparison table
print("\n" + "=" * 80)
print("DETAILED COMPARISON")
print("=" * 80)

models = ['XGBoost', 'RandomForest', 'LogisticRegression']
metrics = ['accuracy', 'precision_1', 'recall_1', 'f1_1', 'roc_auc']
metric_names = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']

for model in models:
    print(f"\n{model}")
    print("-" * 80)
    print(f"  {'Strategy':<35} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'AUC':>8}")
    print(f"  {'-'*75}")
    
    for strategy_name, results in all_results.items():
        if model in results:
            r = results[model]
            acc = r.get('accuracy', 0)
            prec = r.get('precision_1', 0)
            rec = r.get('recall_1', 0)
            f1 = r.get('f1_1', 0)
            auc = r.get('roc_auc', 0)
            print(f"  {strategy_name:<35} {acc:>8.4f} {prec:>8.4f} {rec:>8.4f} {f1:>8.4f} {auc:>8.4f}")

# Find best performing strategy for each model
print("\n" + "=" * 80)
print("BEST PERFORMING STRATEGY PER MODEL")
print("=" * 80)

for model in models:
    print(f"\n{model}:")
    
    for metric, metric_name in zip(metrics, metric_names):
        best_strategy = None
        best_value = -1
        
        for strategy_name, results in all_results.items():
            if model in results:
                value = results[model].get(metric, 0)
                if value > best_value:
                    best_value = value
                    best_strategy = strategy_name
        
        if best_strategy:
            print(f"  {metric_name:<12}: {best_strategy:<35} ({best_value:.4f})")

# Overall recommendation
print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

print("\n1. PERFORMANCE ANALYSIS:")
print("   - Compare F1-Score and ROC-AUC across strategies")
print("   - One-hot encoding typically provides better feature representation")
print("   - Integer encoding may introduce false ordinal relationships")
print("   - No service may underperform if service is truly predictive")

print("\n2. FEATURE IMPORTANCE:")
print("   - Check feature_importance_*_mixed_onehot.png")
print("   - See if individual service features are important")
print("   - Compare with feature_importance_*_mixed.png (standard)")

print("\n3. DEPLOYMENT CONSIDERATIONS:")
print("   - One-hot encoding: More features but better representation")
print("   - Integer encoding: Fewer features but potential bias")
print("   - No service: Simplest but may lose predictive power")

print("\n" + "=" * 80)
print("COMPARISON COMPLETE")
print("=" * 80)

# Save comparison to CSV
comparison_data = []
for strategy_name, results in all_results.items():
    for model in models:
        if model in results:
            r = results[model]
            comparison_data.append({
                'Strategy': strategy_name,
                'Model': model,
                'Accuracy': r.get('accuracy', 0),
                'Precision': r.get('precision_1', 0),
                'Recall': r.get('recall_1', 0),
                'F1-Score': r.get('f1_1', 0),
                'ROC-AUC': r.get('roc_auc', 0),
                'TP': r.get('tp', 0),
                'FP': r.get('fp', 0),
                'TN': r.get('tn', 0),
                'FN': r.get('fn', 0)
            })

df_comparison = pd.DataFrame(comparison_data)
comparison_csv = os.path.join(OUTPUT_DIR, 'comparison_service_encoding.csv')
df_comparison.to_csv(comparison_csv, index=False)
print(f"\nComparison saved to: {comparison_csv}")
