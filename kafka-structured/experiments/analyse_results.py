#!/usr/bin/env python3
"""
Results Analyzer
Computes summary metrics and statistical tests
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
from scipy.stats import mannwhitneyu
import numpy as np

SLO_THRESHOLD_MS = 36.0
RESULTS_DIR = Path("results")
MONITORED_SERVICES = [
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]


def summarise_run(jsonl_path: Path) -> dict:
    """Compute summary metrics for a single run."""
    snapshots = []
    with open(jsonl_path) as f:
        for line in f:
            snapshots.append(json.loads(line))

    if not snapshots:
        return {}

    # Parse metadata from filename
    stem = jsonl_path.stem
    parts = stem.split("_")
    condition = parts[0]
    pattern = parts[1]
    run_id = int(parts[2].replace("run", ""))

    n_intervals = len(snapshots)

    # SLO violation rate
    fe_violations = sum(
        1 for s in snapshots
        if s["services"]["front-end"]["slo_violated"]
    )
    slo_violation_rate = fe_violations / n_intervals

    # Total replica-seconds
    total_replica_seconds = sum(
        sum(s["services"][svc]["replicas"] for svc in MONITORED_SERVICES)
        * 30  # 30 seconds per interval
        for s in snapshots
    )

    # Average replicas
    avg_replicas = total_replica_seconds / (n_intervals * 30 * len(MONITORED_SERVICES))

    # Max replicas
    max_replicas = max(
        sum(s["services"][svc]["replicas"] for svc in MONITORED_SERVICES)
        for s in snapshots
    )

    # Scaling events (count changes in replica count)
    scaling_events = 0
    for svc in MONITORED_SERVICES:
        prev_replicas = snapshots[0]["services"][svc]["replicas"]
        for s in snapshots[1:]:
            curr_replicas = s["services"][svc]["replicas"]
            if curr_replicas != prev_replicas:
                scaling_events += 1
            prev_replicas = curr_replicas

    return {
        "condition": condition,
        "pattern": pattern,
        "run_id": run_id,
        "slo_violation_rate": round(slo_violation_rate, 4),
        "total_replica_seconds": total_replica_seconds,
        "avg_replicas": round(avg_replicas, 2),
        "max_replicas": max_replicas,
        "scaling_events": scaling_events,
        "n_intervals": n_intervals
    }


def compute_statistics(summaries: list[dict]) -> dict:
    """Compute Mann-Whitney U tests comparing proactive vs reactive."""
    results = {}
    
    # Group by pattern
    by_pattern = defaultdict(lambda: {"proactive": [], "reactive": []})
    for s in summaries:
        by_pattern[s["pattern"]][s["condition"]].append(s)
    
    metrics = ["slo_violation_rate", "total_replica_seconds", "avg_replicas", "scaling_events"]
    
    for pattern, data in by_pattern.items():
        results[pattern] = {}
        
        for metric in metrics:
            proactive_vals = [r[metric] for r in data["proactive"]]
            reactive_vals = [r[metric] for r in data["reactive"]]
            
            if len(proactive_vals) < 2 or len(reactive_vals) < 2:
                results[pattern][metric] = {
                    "proactive_mean": np.mean(proactive_vals) if proactive_vals else 0,
                    "reactive_mean": np.mean(reactive_vals) if reactive_vals else 0,
                    "p_value": None,
                    "significant": False
                }
                continue
            
            # Mann-Whitney U test
            statistic, p_value = mannwhitneyu(proactive_vals, reactive_vals, alternative='two-sided')
            
            results[pattern][metric] = {
                "proactive_mean": round(np.mean(proactive_vals), 4),
                "proactive_std": round(np.std(proactive_vals), 4),
                "reactive_mean": round(np.mean(reactive_vals), 4),
                "reactive_std": round(np.std(reactive_vals), 4),
                "p_value": round(p_value, 4),
                "significant": p_value < 0.05
            }
    
    return results


def main():
    """Main entry point."""
    print("Analyzing experiment results...")
    
    # Find all result files
    result_files = list(RESULTS_DIR.glob("*.jsonl"))
    print(f"Found {len(result_files)} result files")
    
    if not result_files:
        print("No results to analyze")
        return
    
    # Summarize each run
    summaries = []
    for path in result_files:
        summary = summarise_run(path)
        if summary:
            summaries.append(summary)
    
    print(f"Summarized {len(summaries)} runs")
    
    # Write summary CSV
    summary_path = RESULTS_DIR / "summary.csv"
    with open(summary_path, "w", newline="") as f:
        fieldnames = ["condition", "pattern", "run_id", "slo_violation_rate",
                     "total_replica_seconds", "avg_replicas", "max_replicas",
                     "scaling_events", "n_intervals"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)
    
    print(f"Summary written to: {summary_path}")
    
    # Compute statistics
    stats = compute_statistics(summaries)
    
    # Write statistics JSON
    stats_path = RESULTS_DIR / "statistics.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"Statistics written to: {stats_path}")
    
    # Write statistics CSV (Task 9.4)
    stats_csv_path = RESULTS_DIR / "statistics.csv"
    with open(stats_csv_path, "w", newline="") as f:
        fieldnames = ["pattern", "metric", "proactive_mean", "proactive_std",
                     "reactive_mean", "reactive_std", "p_value", "significant"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for pattern, metrics in stats.items():
            for metric, values in metrics.items():
                row = {
                    "pattern": pattern,
                    "metric": metric,
                    "proactive_mean": values["proactive_mean"],
                    "proactive_std": values.get("proactive_std", 0),
                    "reactive_mean": values["reactive_mean"],
                    "reactive_std": values.get("reactive_std", 0),
                    "p_value": values.get("p_value", ""),
                    "significant": values.get("significant", False)
                }
                writer.writerow(row)
    
    print(f"Statistics CSV written to: {stats_csv_path}")
    
    # Print summary table (Task 9.5 - Enhanced for research paper)
    print("\n" + "="*90)
    print("PROACTIVE VS REACTIVE AUTOSCALING - EXPERIMENTAL RESULTS")
    print("="*90)
    print(f"\nTotal runs analyzed: {len(summaries)}")
    print(f"Conditions: Proactive (ML-based) vs Reactive (HPA CPU-based)")
    print(f"SLO Threshold: {SLO_THRESHOLD_MS}ms (p95 latency)")
    
    # Table header
    print("\n" + "-"*90)
    print(f"{'Pattern':<12} {'Metric':<25} {'Proactive':<15} {'Reactive':<15} {'p-value':<10} {'Sig':<5}")
    print("-"*90)
    
    for pattern in ["constant", "step", "spike", "ramp"]:
        if pattern not in stats:
            continue
        
        metrics_data = stats[pattern]
        first_metric = True
        
        for metric in ["slo_violation_rate", "total_replica_seconds", "avg_replicas", "scaling_events"]:
            if metric not in metrics_data:
                continue
            
            values = metrics_data[metric]
            pro_mean = values["proactive_mean"]
            pro_std = values.get("proactive_std", 0)
            react_mean = values["reactive_mean"]
            react_std = values.get("reactive_std", 0)
            p_val = values.get("p_value", "N/A")
            sig = "***" if values.get("significant", False) else ""
            
            # Format metric name
            metric_display = metric.replace("_", " ").title()
            
            # Format values with std dev
            pro_str = f"{pro_mean:.4f}±{pro_std:.4f}"
            react_str = f"{react_mean:.4f}±{react_std:.4f}"
            p_str = f"{p_val:.4f}" if isinstance(p_val, float) else str(p_val)
            
            # Pattern name only on first row
            pattern_display = pattern.capitalize() if first_metric else ""
            
            print(f"{pattern_display:<12} {metric_display:<25} {pro_str:<15} {react_str:<15} {p_str:<10} {sig:<5}")
            first_metric = False
        
        print("-"*90)
    
    print("\n*** = Statistically significant difference (p < 0.05)")
    print("="*90)


if __name__ == "__main__":
    main()
