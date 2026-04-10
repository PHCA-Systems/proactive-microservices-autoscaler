"""
Apply SLA violation labels to ALL runs (including runs 5-7)
Based on the methodology from RESULTS.md:
- SLA threshold: 35.68ms (P75 of front-end p95 under constant load, 50 users)
- Lookahead: 2 windows (same as original runs)
"""

import pandas as pd
import numpy as np
import os
import csv

# Configuration
DATA_BASE = os.path.join(os.path.dirname(__file__), "../../data/gke")
P95_SLA_THRESHOLD_MS = 35.68
LOOKAHEAD_WINDOWS = 2

PATTERNS = ['constant', 'ramp', 'spike', 'step']
RUNS_TO_LABEL = {
    'constant': [],  # Already labeled
    'ramp': [5, 6, 7],
    'spike': [5, 6, 7],
    'step': [5, 6, 7]
}

print("=" * 80)
print("APPLYING SLA LABELS TO UNLABELED RUNS")
print("=" * 80)
print(f"\nSLA Threshold: {P95_SLA_THRESHOLD_MS}ms (p95 latency)")
print(f"Lookahead windows: {LOOKAHEAD_WINDOWS}")

def apply_sla_labels(csv_path):
    """Apply SLA violation labels to a CSV file"""
    # Load data
    df = pd.read_csv(csv_path)
    
    # Group by service to apply lookahead labeling
    services = df['service'].unique()
    labeled_rows = []
    
    for service in services:
        service_df = df[df['service'] == service].copy().reset_index(drop=True)
        
        # Extract p95 latency history
        p95_history = service_df['p95_latency_ms'].values
        
        # Apply lookahead labeling
        for i in range(len(service_df)):
            row = service_df.iloc[i].to_dict()
            
            # Look ahead at next LOOKAHEAD_WINDOWS samples
            start_idx = i
            end_idx = min(i + 1 + LOOKAHEAD_WINDOWS, len(p95_history))
            future_p95 = p95_history[start_idx:end_idx]
            
            # Check if any future p95 exceeds threshold
            violated = any(v > P95_SLA_THRESHOLD_MS for v in future_p95)
            row['sla_violated'] = int(violated)
            
            labeled_rows.append(row)
    
    # Create labeled dataframe
    df_labeled = pd.DataFrame(labeled_rows)
    
    # Statistics
    total = len(df_labeled)
    violations = df_labeled['sla_violated'].sum()
    
    return df_labeled, total, violations

# Process all unlabeled runs
total_processed = 0
summary = []

for pattern in PATTERNS:
    for run_num in RUNS_TO_LABEL[pattern]:
        csv_path = os.path.join(DATA_BASE, f"experiments/{pattern}/run_{run_num}/metrics.csv")
        
        if not os.path.exists(csv_path):
            print(f"WARNING: Missing {csv_path}")
            continue
        
        print(f"\nProcessing {pattern}/run_{run_num}...")
        
        # Apply labels
        df_labeled, total, violations = apply_sla_labels(csv_path)
        
        # Save back to same file
        df_labeled.to_csv(csv_path, index=False)
        
        print(f"  ✓ Labeled: {total} rows, {violations} violations ({violations/total*100:.1f}%)")
        
        summary.append({
            'pattern': pattern,
            'run': f'run_{run_num}',
            'rows': total,
            'violations': violations,
            'rate': violations/total*100
        })
        
        total_processed += 1

# Summary
print("\n" + "=" * 80)
print("LABELING SUMMARY")
print("=" * 80)
print(f"\nTotal runs processed: {total_processed}")
print(f"\n{'Pattern':<10} {'Run':<8} {'Rows':>6} {'Violations':>12} {'Rate':>8}")
print("-" * 50)
for s in summary:
    print(f"{s['pattern']:<10} {s['run']:<8} {s['rows']:>6} {s['violations']:>12} {s['rate']:>7.1f}%")

print("\n" + "=" * 80)
print("LABELING COMPLETE")
print("=" * 80)
print("\nNow run: python prepare_data.py")
