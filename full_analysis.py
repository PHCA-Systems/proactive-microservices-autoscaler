#!/usr/bin/env python3
"""
Full Academic Analysis Pipeline
Processes all 34 experiment runs and generates paper-ready comparison tables.
"""
import json
import os
from pathlib import Path
from collections import defaultdict

try:
    from scipy import stats
except ImportError:
    import subprocess
    subprocess.run(["python", "-m", "pip", "install", "scipy"], check=True)
    from scipy import stats

RESULTS_DIR = Path("kafka-structured/experiments/results")
MONITORED = ["front-end", "carts", "orders", "catalogue", "user", "payment", "shipping"]
SLO = 35.68
PATTERNS = ["constant", "step", "spike", "ramp"]


def load_run(filepath):
    """Load JSONL, filtering out settle-phase snapshots."""
    data = []
    for line in open(filepath):
        snap = json.loads(line)
        if snap.get("phase") != "settle":
            data.append(snap)
    return data


def analyze_run(data):
    """Compute per-service metrics for a single run."""
    results = {}
    for svc in MONITORED:
        violations = sum(1 for s in data if s["services"][svc]["p95_ms"] > SLO)
        vr = violations / len(data) * 100 if data else 0
        p95_vals = [s["services"][svc]["p95_ms"] for s in data if s["services"][svc]["p95_ms"] > 0]
        avg_p95 = sum(p95_vals) / len(p95_vals) if p95_vals else 0
        max_p95 = max(p95_vals) if p95_vals else 0
        rep_secs = sum(s["services"][svc].get("replicas", 1) * 30 for s in data)
        max_reps = max(s["services"][svc].get("replicas", 1) for s in data)
        results[svc] = {
            "violation_rate": vr,
            "avg_p95": avg_p95,
            "max_p95": max_p95,
            "replica_seconds": rep_secs,
            "max_replicas": max_reps,
            "p95_values": p95_vals,
            "violations": violations,
            "total_intervals": len(data),
        }
    return results


# Collect all runs
pro_runs = defaultdict(list)  # pattern -> [run_results]
rea_runs = defaultdict(list)

for f in sorted(RESULTS_DIR.glob("*.jsonl")):
    name = f.stem
    if name.startswith("diag_"):
        continue  # Skip diagnostic runs
    parts = name.split("_")
    if len(parts) < 3:
        continue
    condition = parts[0]  # proactive or reactive
    pattern = parts[1]    # constant, step, spike, ramp
    data = load_run(f)
    if not data:
        print(f"WARNING: Empty file {f.name}")
        continue
    results = analyze_run(data)
    if condition == "proactive":
        pro_runs[pattern].append(results)
    elif condition == "reactive":
        rea_runs[pattern].append(results)

print("\n" + "=" * 120)
print("  FULL EXPERIMENT RESULTS - 34-Run Academic Analysis")
print("=" * 120)

# Per-pattern analysis
for pattern in PATTERNS:
    pro_list = pro_runs.get(pattern, [])
    rea_list = rea_runs.get(pattern, [])
    if not pro_list or not rea_list:
        print(f"\n  [SKIP] {pattern}: no data (pro={len(pro_list)}, rea={len(rea_list)})")
        continue

    print(f"\n{'=' * 120}")
    print(f"  PATTERN: {pattern.upper()} ({len(pro_list)} proactive runs, {len(rea_list)} reactive runs)")
    print(f"{'=' * 120}")
    print(f"  {'Service':<12} | {'Pro VR%':>9} | {'Rea VR%':>9} | {'Pro p95':>9} | {'Rea p95':>9} | {'Pro RepSec':>10} | {'Rea RepSec':>10} | {'MW-U p':>10} | {'Winner'}")
    print("  " + "-" * 108)

    for svc in MONITORED:
        # Average across runs
        pro_vrs = [r[svc]["violation_rate"] for r in pro_list]
        rea_vrs = [r[svc]["violation_rate"] for r in rea_list]
        pro_p95s = [r[svc]["avg_p95"] for r in pro_list]
        rea_p95s = [r[svc]["avg_p95"] for r in rea_list]
        pro_reps = [r[svc]["replica_seconds"] for r in pro_list]
        rea_reps = [r[svc]["replica_seconds"] for r in rea_list]

        avg_pro_vr = sum(pro_vrs) / len(pro_vrs)
        avg_rea_vr = sum(rea_vrs) / len(rea_vrs)
        avg_pro_p95 = sum(pro_p95s) / len(pro_p95s)
        avg_rea_p95 = sum(rea_p95s) / len(rea_p95s)
        avg_pro_rep = sum(pro_reps) / len(pro_reps)
        avg_rea_rep = sum(rea_reps) / len(rea_reps)

        # Mann-Whitney U test on violation rates
        p_str = "N/A"
        if len(pro_vrs) >= 2 and len(rea_vrs) >= 2:
            try:
                stat, pval = stats.mannwhitneyu(pro_vrs, rea_vrs, alternative='two-sided')
                p_str = f"{pval:.4f}"
                if pval < 0.05:
                    p_str += " *"
            except ValueError:
                p_str = "Tied"

        winner = "TIE"
        if avg_pro_vr < avg_rea_vr - 1:
            winner = "PROACTIVE"
        elif avg_rea_vr < avg_pro_vr - 1:
            winner = "REACTIVE"

        print(f"  {svc:<12} | {avg_pro_vr:>8.1f}% | {avg_rea_vr:>8.1f}% | {avg_pro_p95:>7.1f}ms | {avg_rea_p95:>7.1f}ms | {avg_pro_rep:>10.0f} | {avg_rea_rep:>10.0f} | {p_str:>10} | {winner}")

# Global summary across ALL patterns
print(f"\n{'=' * 120}")
print(f"  GLOBAL SUMMARY (All Patterns Combined)")
print(f"{'=' * 120}")

all_pro_vr, all_rea_vr = [], []
all_pro_p95, all_rea_p95 = [], []
total_pro_reps, total_rea_reps = 0, 0

for pattern in PATTERNS:
    for run in pro_runs.get(pattern, []):
        for svc in MONITORED:
            all_pro_vr.append(run[svc]["violation_rate"])
            all_pro_p95.append(run[svc]["avg_p95"])
            total_pro_reps += run[svc]["replica_seconds"]
    for run in rea_runs.get(pattern, []):
        for svc in MONITORED:
            all_rea_vr.append(run[svc]["violation_rate"])
            all_rea_p95.append(run[svc]["avg_p95"])
            total_rea_reps += run[svc]["replica_seconds"]

if all_pro_vr and all_rea_vr:
    g_pro_vr = sum(all_pro_vr) / len(all_pro_vr)
    g_rea_vr = sum(all_rea_vr) / len(all_rea_vr)
    g_pro_p95 = sum(all_pro_p95) / len(all_pro_p95)
    g_rea_p95 = sum(all_rea_p95) / len(all_rea_p95)

    stat, pval = stats.mannwhitneyu(all_pro_vr, all_rea_vr, alternative='two-sided')
    p_str = f"{pval:.6f}"
    if pval < 0.05:
        p_str += " ***"

    print(f"  Proactive Global Violation Rate: {g_pro_vr:.1f}%")
    print(f"  Reactive  Global Violation Rate: {g_rea_vr:.1f}%")
    print(f"  Violation Reduction:             {g_rea_vr - g_pro_vr:.1f} percentage points")
    print(f"  Proactive Mean p95:              {g_pro_p95:.1f}ms")
    print(f"  Reactive  Mean p95:              {g_rea_p95:.1f}ms")
    if g_rea_p95 > 0:
        print(f"  Latency Improvement:             {((g_rea_p95 - g_pro_p95) / g_rea_p95 * 100):.1f}%")
    print(f"  Proactive Replica-Seconds:       {total_pro_reps}")
    print(f"  Reactive  Replica-Seconds:       {total_rea_reps}")
    if total_rea_reps > 0:
        print(f"  Resource Savings:                {(1 - total_pro_reps / total_rea_reps) * 100:.1f}%")
    print(f"  Mann-Whitney U p-value:          {p_str}")
    print(f"  Statistically Significant:       {'YES' if pval < 0.05 else 'NO'}")

print(f"\n{'=' * 120}")
print("  Analysis complete.")
print(f"{'=' * 120}\n")
