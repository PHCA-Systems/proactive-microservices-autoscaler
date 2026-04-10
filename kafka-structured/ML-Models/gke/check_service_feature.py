"""
Check if service feature is problematic in GKE dataset
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("ANALYZING SERVICE FEATURE IN GKE DATASET")
print("=" * 80)

# Load GKE mixed dataset
df_gke = pd.read_csv('gke_mixed_dataset.csv')

print("\n1. SERVICE DISTRIBUTION (GKE Mixed)")
print("-" * 80)
service_names = ['catalogue', 'carts', 'front-end', 'orders', 'payment', 'shipping', 'user']
service_counts = df_gke['service'].value_counts().sort_index()
print(f"{'Service':<15} {'Code':>5} {'Count':>8} {'Percentage':>12}")
print("-" * 80)
for code, count in service_counts.items():
    name = service_names[code] if code < len(service_names) else f'unknown_{code}'
    pct = count / len(df_gke) * 100
    print(f"{name:<15} {code:>5} {count:>8} {pct:>11.1f}%")

print(f"\nTotal rows: {len(df_gke)}")

print("\n2. VIOLATIONS BY SERVICE (GKE Mixed)")
print("-" * 80)
print(f"{'Service':<15} {'Violations':>12} {'Total':>8} {'Rate':>8}")
print("-" * 80)
for code in sorted(df_gke['service'].unique()):
    service_df = df_gke[df_gke['service'] == code]
    violations = service_df['sla_violated'].sum()
    total = len(service_df)
    rate = violations / total * 100
    name = service_names[code] if code < len(service_names) else f'unknown_{code}'
    print(f"{name:<15} {violations:>12} {total:>8} {rate:>7.1f}%")

total_violations = df_gke['sla_violated'].sum()
print(f"\n{'TOTAL':<15} {total_violations:>12} {len(df_gke):>8} {total_violations/len(df_gke)*100:>7.1f}%")

print("\n3. CHECKING FOR ISSUES")
print("-" * 80)

# Check if service is perfectly correlated with violations
service_violation_corr = df_gke[['service', 'sla_violated']].corr().iloc[0, 1]
print(f"Correlation between service and sla_violated: {service_violation_corr:.4f}")

# Check if certain services ALWAYS violate or NEVER violate
print("\nServices with extreme violation rates:")
for code in sorted(df_gke['service'].unique()):
    service_df = df_gke[df_gke['service'] == code]
    violations = service_df['sla_violated'].sum()
    total = len(service_df)
    rate = violations / total * 100
    name = service_names[code] if code < len(service_names) else f'unknown_{code}'
    if rate == 0:
        print(f"  ⚠️  {name}: NEVER violates (0%)")
    elif rate == 100:
        print(f"  ⚠️  {name}: ALWAYS violates (100%)")
    elif rate > 50:
        print(f"  ⚠️  {name}: High violation rate ({rate:.1f}%)")

# Check if service is the only feature with values
print("\n4. FEATURE VALUE RANGES")
print("-" * 80)
features = ['service', 'request_rate_rps', 'error_rate_pct', 'p50_latency_ms', 
            'p95_latency_ms', 'p99_latency_ms', 'cpu_usage_pct', 'memory_usage_mb',
            'delta_rps', 'delta_p95_latency_ms', 'delta_cpu_usage_pct']

print(f"{'Feature':<25} {'Min':>10} {'Max':>10} {'Mean':>10} {'Non-zero %':>12}")
print("-" * 80)
for feat in features:
    if feat in df_gke.columns:
        min_val = df_gke[feat].min()
        max_val = df_gke[feat].max()
        mean_val = df_gke[feat].mean()
        non_zero_pct = (df_gke[feat] != 0).sum() / len(df_gke) * 100
        print(f"{feat:<25} {min_val:>10.2f} {max_val:>10.2f} {mean_val:>10.2f} {non_zero_pct:>11.1f}%")

print("\n5. COMPARISON WITH LOCAL DATASET")
print("-" * 80)

# Load local dataset
df_local = pd.read_csv('../../data/local/mixed_4hour_metrics.csv')

print("\nLOCAL SERVICE DISTRIBUTION:")
print(f"{'Service':<15} {'Count':>8} {'Percentage':>12}")
print("-" * 80)
for service_name in service_names:
    count = (df_local['service'] == service_name).sum()
    pct = count / len(df_local) * 100
    print(f"{service_name:<15} {count:>8} {pct:>11.1f}%")

print("\nLOCAL VIOLATIONS BY SERVICE:")
print(f"{'Service':<15} {'Violations':>12} {'Total':>8} {'Rate':>8}")
print("-" * 80)
for service_name in service_names:
    service_df = df_local[df_local['service'] == service_name]
    violations = service_df['sla_violated'].sum()
    total = len(service_df)
    rate = violations / total * 100 if total > 0 else 0
    print(f"{service_name:<15} {violations:>12} {total:>8} {rate:>7.1f}%")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
