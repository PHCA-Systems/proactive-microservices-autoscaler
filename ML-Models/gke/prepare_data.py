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
EXPERIMENTS_BASE = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR       = os.path.dirname(__file__)
OUTPUT_CSV       = os.path.join(OUTPUT_DIR, "gke_combined.csv")

# Same service mapping as local pipeline, minus queue-master
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

# ── Load all runs ─────────────────────────────────────────────────────────────
print("=" * 70)
print("PHASE 1: DATA PREPARATION")
print("=" * 70)

all_rows = []
run_summary = []

for pattern in PATTERNS:
    pdir = os.path.join(EXPERIMENTS_BASE, pattern)
    if not os.path.isdir(pdir):
        continue
    for run in sorted(os.listdir(pdir)):
        csv_path = os.path.join(pdir, run, "sockshop_metrics.csv")
        if not os.path.exists(csv_path):
            continue
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        violations = sum(1 for r in rows if r['sla_violated'] == '1')
        run_summary.append({
            'pattern': pattern,
            'run': run,
            'rows': len(rows),
            'violations': violations,
            'violation_pct': round(violations / len(rows) * 100, 1)
        })
        for row in rows:
            row['pattern'] = pattern
        all_rows.extend(rows)

print(f"\nRuns loaded:")
print(f"  {'Pattern':<10} {'Run':<8} {'Rows':>6} {'Violations':>10} {'Pct':>6}")
print(f"  {'-'*45}")
for s in run_summary:
    print(f"  {s['pattern']:<10} {s['run']:<8} {s['rows']:>6} {s['violations']:>10} {s['violation_pct']:>5}%")

# ── Build DataFrame ───────────────────────────────────────────────────────────
df = pd.DataFrame(all_rows)

print(f"\nRaw dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"Patterns: {df['pattern'].value_counts().to_dict()}")
print(f"Services: {sorted(df['service'].unique())}")

# Drop timestamp (not a feature)
df = df.drop(columns=['timestamp'])

# Encode service
df['service'] = df['service'].map(SERVICE_MAPPING)
unmapped = df['service'].isna().sum()
if unmapped > 0:
    print(f"WARNING: {unmapped} rows with unmapped service — dropping")
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
print(f"\nNaN values filled: {nan_before}")
print(f"Inf values filled: {inf_before}")

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(df)
violations = df['sla_violated'].sum()
print(f"\nFinal dataset: {total} rows")
print(f"Violations: {violations} ({round(violations/total*100, 2)}%)")
print(f"No violation: {total - violations} ({round((total-violations)/total*100, 2)}%)")

print(f"\nPer-pattern violation rate:")
for p in PATTERNS:
    sub = df[df['pattern'] == p]
    v = sub['sla_violated'].sum()
    print(f"  {p:<10} {v}/{len(sub)} ({round(v/len(sub)*100,1)}%)")

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved: {OUTPUT_CSV}")
print(f"Columns: {list(df.columns)}")
