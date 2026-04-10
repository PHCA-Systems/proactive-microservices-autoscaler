"""
Analyze the actual datasets used for Local vs GKE training
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("DATASET ANALYSIS: LOCAL vs GKE")
print("=" * 80)

# Load datasets
df_local = pd.read_csv('../../data/local/mixed_4hour_metrics.csv')
df_gke_mix = pd.read_csv('gke_mixed_dataset.csv')

print("\n" + "=" * 80)
print("LOCAL DATASET (mixed_4hour_metrics.csv)")
print("=" * 80)
print(f"Total rows: {len(df_local)}")
print(f"Violations: {df_local['sla_violated'].sum()} ({df_local['sla_violated'].sum()/len(df_local)*100:.1f}%)")
print(f"Services: {sorted(df_local['service'].unique())}")
print(f"Columns: {list(df_local.columns)}")
print(f"\nTimestamp range:")
print(f"  Start: {df_local['timestamp'].iloc[0]}")
print(f"  End: {df_local['timestamp'].iloc[-1]}")

# Calculate duration
from datetime import datetime
start = pd.to_datetime(df_local['timestamp'].iloc[0])
end = pd.to_datetime(df_local['timestamp'].iloc[-1])
duration = (end - start).total_seconds() / 3600
print(f"  Duration: {duration:.2f} hours")

# Per-service stats
print(f"\nPer-service violations:")
for service in sorted(df_local['service'].unique()):
    service_df = df_local[df_local['service'] == service]
    violations = service_df['sla_violated'].sum()
    print(f"  {service:15s}: {violations:3d}/{len(service_df):4d} ({violations/len(service_df)*100:5.1f}%)")

print("\n" + "=" * 80)
print("GKE MIXED DATASET (gke_mixed_dataset.csv)")
print("=" * 80)
print(f"Total rows: {len(df_gke_mix)}")
print(f"Violations: {df_gke_mix['sla_violated'].sum()} ({df_gke_mix['sla_violated'].sum()/len(df_gke_mix)*100:.1f}%)")
print(f"Services: {sorted(df_gke_mix['service'].unique())}")
print(f"Columns: {list(df_gke_mix.columns)}")

# Per-service stats
print(f"\nPer-service violations:")
service_names = ['catalogue', 'carts', 'front-end', 'orders', 'payment', 'shipping', 'user']
for i, service in enumerate(service_names):
    service_df = df_gke_mix[df_gke_mix['service'] == i]
    violations = service_df['sla_violated'].sum()
    print(f"  {service:15s}: {violations:3d}/{len(service_df):4d} ({violations/len(service_df)*100:5.1f}%)")

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
print(f"\n{'Metric':<30} {'Local':>15} {'GKE Mixed':>15} {'Ratio':>10}")
print("-" * 75)
print(f"{'Total Rows':<30} {len(df_local):>15,} {len(df_gke_mix):>15,} {len(df_gke_mix)/len(df_local):>10.2f}x")
print(f"{'Violations':<30} {df_local['sla_violated'].sum():>15,} {df_gke_mix['sla_violated'].sum():>15,} {df_gke_mix['sla_violated'].sum()/df_local['sla_violated'].sum():>10.2f}x")
print(f"{'Violation Rate':<30} {df_local['sla_violated'].sum()/len(df_local)*100:>14.1f}% {df_gke_mix['sla_violated'].sum()/len(df_gke_mix)*100:>14.1f}%")
print(f"{'Services':<30} {len(df_local['service'].unique()):>15} {len(df_gke_mix['service'].unique()):>15}")
print(f"{'Duration':<30} {'~4 hours':>15} {'~4 hours':>15}")
print(f"{'Environment':<30} {'Docker (local)':>15} {'GKE (cloud)':>15}")

print("\n" + "=" * 80)
print("KEY DIFFERENCES")
print("=" * 80)
print(f"""
1. DATASET SIZE:
   - Local: {len(df_local):,} rows
   - GKE: {len(df_gke_mix):,} rows
   - GKE has {len(df_gke_mix)/len(df_local):.1f}x more data

2. VIOLATION RATE:
   - Local: {df_local['sla_violated'].sum()/len(df_local)*100:.1f}%
   - GKE: {df_gke_mix['sla_violated'].sum()/len(df_gke_mix)*100:.1f}%
   - Local is more imbalanced

3. ENVIRONMENT:
   - Local: Docker containers on single machine
   - GKE: Distributed cloud infrastructure

4. BOTH ARE MIXED 4-HOUR WORKLOADS:
   - Both datasets are continuous 4-hour runs
   - Both contain mixed load patterns
   - Main difference is SIZE and ENVIRONMENT, not pattern type
""")

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
