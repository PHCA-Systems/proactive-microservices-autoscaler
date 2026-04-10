"""
Phase 1: Data Preparation
Merges all 16 per-pattern runs into a single labeled dataset.
Mirrors the preprocessing pipeline from kafka-structured/ML-Models/train_models.py
with adjustments for the GKE dataset (7 services, cloud latency profile).
"""

import csv
import os
import math
import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
DATA_BASE = os.path.join(os.path.dirname(__file__), "../../data/gke")
OUTPUT_DIR = os.path.dirname(__file__)

# Same service mapping as local pipeline
SERVICE_MAPPING = {
    'catalogue': 0,
    'carts':     1,
    'front-end': 2,
    'orders':    3,
    'payment':   4,
    'shipping':  5,
    'user':      6,
}

PATTERNS = ['constant', 'ramp', 'spike', 'step']

# Dataset configurations
SEPARATED_RUNS = {
    'constant': [1, 2, 3, 4],
    'ramp': [1, 2, 3, 4, 5, 6, 7],
    'spike': [1, 2, 3, 4, 5, 6, 7],
    'step': [1, 2, 3, 4, 5, 6, 7]
}

# ── Load separated runs ───────────────────────────────────────────────────────
print("=" * 80)
print("DATASET 1: SEPARATED RUNS (15-min patterns)")
print("=" * 80)

separated_rows = []
run_summary = []

for pattern in PATTERNS:
    for run_num in SEPARATED_RUNS[pattern]:
        csv_path = os.path.join(DATA_BASE, f"experiments/{pattern}/run_{run_num}/metrics.csv")
        if not os.path.exists(csv_path):
            print(f"WARNING: Missing {csv_path}")
            continue
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        violations = sum(1 for r in rows if r['sla_violated'] == '1')
        run_summary.append({
            'pattern': pattern,
            'run': f'run_{run_num}',
            'rows': len(rows),
            'violations': violations,
            'violation_pct': round(violations / len(rows) * 100, 1)
        })
        for row in rows:
            row['pattern'] = pattern
        separated_rows.extend(rows)

print(f"\nRuns loaded:")
print(f"  {'Pattern':<10} {'Run':<8} {'Rows':>6} {'Violations':>10} {'Pct':>6}")
print(f"  {'-'*45}")
for s in run_summary:
    print(f"  {s['pattern']:<10} {s['run']:<8} {s['rows']:>6} {s['violations']:>10} {s['violation_pct']:>5}%")

# ── Build Separated DataFrame ─────────────────────────────────────────────────
df_separated = pd.DataFrame(separated_rows)

print(f"\nRaw separated dataset: {df_separated.shape[0]} rows, {df_separated.shape[1]} columns")
print(f"Patterns: {df_separated['pattern'].value_counts().to_dict()}")

# Preprocess separated dataset
def preprocess_df(df, name):
    print(f"\nPreprocessing {name}...")
    # Drop timestamp
    df = df.drop(columns=['timestamp'])
    
    # Encode service (same mapping as local)
    df['service'] = df['service'].map(SERVICE_MAPPING)
    unmapped = df['service'].isna().sum()
    if unmapped > 0:
        print(f"  WARNING: {unmapped} rows with unmapped service — dropping")
        df = df.dropna(subset=['service'])
    df['service'] = df['service'].astype(int)
    
    # Cast numeric columns
    numeric_cols = [
        'request_rate_rps', 'error_rate_pct', 'p50_latency_ms', 'p95_latency_ms',
        'p99_latency_ms', 'cpu_usage_pct', 'memory_usage_mb',
        'delta_rps', 'delta_p95_latency_ms', 'delta_cpu_usage_pct'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Cast target
    df['sla_violated'] = pd.to_numeric(df['sla_violated'], errors='coerce').astype(int)
    
    # NaN / inf handling (same as local pipeline)
    nan_before = df[numeric_cols].isna().sum().sum()
    inf_before = np.isinf(df[numeric_cols].select_dtypes(include=[np.number])).sum().sum()
    df = df.replace([np.inf, -np.inf], np.nan)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    print(f"  NaN values filled: {nan_before}")
    print(f"  Inf values filled: {inf_before}")
    
    total = len(df)
    violations = df['sla_violated'].sum()
    print(f"  Final: {total} rows, {violations} violations ({round(violations/total*100, 2)}%)")
    
    return df

df_separated = preprocess_df(df_separated, "SEPARATED")

print(f"\nPer-pattern violation rate (separated):")
for p in PATTERNS:
    sub = df_separated[df_separated['pattern'] == p]
    v = sub['sla_violated'].sum()
    print(f"  {p:<10} {v}/{len(sub)} ({round(v/len(sub)*100,1)}%)")

# ── Load and preprocess mixed dataset ─────────────────────────────────────────
print("\n" + "=" * 80)
print("DATASET 2: MIXED RUN (4-hour)")
print("=" * 80)

mixed_path = os.path.join(DATA_BASE, "mixed/metrics_labeled.csv")
if os.path.exists(mixed_path):
    df_mixed = pd.read_csv(mixed_path)
    df_mixed['pattern'] = 'mixed'
    print(f"Loaded: {len(df_mixed)} rows")
    df_mixed = preprocess_df(df_mixed, "MIXED")
else:
    print(f"WARNING: Mixed dataset not found at {mixed_path}")
    df_mixed = None

# ── Save ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SAVING DATASETS")
print("=" * 80)

separated_csv = os.path.join(OUTPUT_DIR, "gke_separated_dataset.csv")
df_separated.to_csv(separated_csv, index=False)
print(f"✓ Saved: {separated_csv}")

if df_mixed is not None:
    mixed_csv = os.path.join(OUTPUT_DIR, "gke_mixed_dataset.csv")
    df_mixed.to_csv(mixed_csv, index=False)
    print(f"✓ Saved: {mixed_csv}")

print(f"\nColumns: {list(df_separated.columns)}")
print("\n" + "=" * 80)
print("DATA PREPARATION COMPLETE")
print("=" * 80)
