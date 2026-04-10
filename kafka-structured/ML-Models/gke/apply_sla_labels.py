"""
Apply SLA violation labels to the mixed dataset
Based on the methodology from RESULTS.md:
- SLA threshold: 35.68ms (P75 of front-end p95 under constant load, 50 users)
- Lookahead: 2 windows (same as separated runs)
"""

import pandas as pd
import numpy as np
import os

# Configuration
DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/gke/mixed/metrics.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../../data/gke/mixed/metrics_labeled.csv")

# SLA threshold from RESULTS.md
P95_SLA_THRESHOLD_MS = 35.68
LOOKAHEAD_WINDOWS = 2

print("=" * 80)
print("APPLYING SLA LABELS TO MIXED DATASET")
print("=" * 80)
print(f"\nSLA Threshold: {P95_SLA_THRESHOLD_MS}ms (p95 latency)")
print(f"Lookahead windows: {LOOKAHEAD_WINDOWS}")

# Load data
df = pd.read_csv(DATA_PATH)
print(f"\nLoaded: {len(df)} rows")
print(f"Columns: {list(df.columns)}")

# Group by service to apply lookahead labeling
services = df['service'].unique()
print(f"\nServices: {sorted(services)}")

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
print(f"\nLabeling complete:")
print(f"  Total rows: {total}")
print(f"  Violations: {violations} ({violations/total*100:.1f}%)")
print(f"  No violations: {total - violations} ({(total-violations)/total*100:.1f}%)")

# Per-service breakdown
print(f"\nPer-service violations:")
for service in sorted(services):
    service_df = df_labeled[df_labeled['service'] == service]
    v = service_df['sla_violated'].sum()
    print(f"  {service}: {v}/{len(service_df)} ({v/len(service_df)*100:.1f}%)")

# Save
df_labeled.to_csv(OUTPUT_PATH, index=False)
print(f"\n✓ Saved labeled dataset: {OUTPUT_PATH}")

print("\n" + "=" * 80)
print("LABELING COMPLETE")
print("=" * 80)
