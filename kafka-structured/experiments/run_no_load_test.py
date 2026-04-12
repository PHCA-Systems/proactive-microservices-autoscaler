#!/usr/bin/env python3
"""
No-Load Test - Collect metrics without any load generation
Tests if SLO violations occur even without traffic
"""

import time
import json
from pathlib import Path
from datetime import datetime
from kubernetes import client, config
import requests
import os

from run_config import (
    MONITORED_SERVICES, NAMESPACE, POLL_INTERVAL_S, 
    SLO_THRESHOLD_MS
)

config.load_kube_config()
apps_v1 = client.AppsV1Api()

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://34.170.213.190:9090")


def query_prometheus(query: str) -> float:
    """Query Prometheus and return the first result value."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "success" and data["data"]["result"]:
            value_str = data["data"]["result"][0]["value"][1]
            if value_str == "NaN" or value_str == "+Inf" or value_str == "-Inf":
                return 0.0
            value = float(value_str)
            if value != value:  # NaN check
                return 0.0
            return value
        return 0.0
    except Exception as e:
        print(f"    Warning: Prometheus query failed: {e}")
        return 0.0


def query_prometheus_for_service(query: str, service_name: str) -> float:
    """Query Prometheus and extract value for a specific service."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "success" and data["data"]["result"]:
            values = []
            for result in data["data"]["result"]:
                metric = result.get("metric", {})
                svc = metric.get("service") or metric.get("job", "")
                
                # Normalize job names
                if svc == "cart":
                    svc = "carts"
                elif svc == "frontend":
                    svc = "front-end"
                
                if svc == service_name:
                    value_str = result["value"][1]
                    if value_str not in ("NaN", "+Inf", "-Inf"):
                        value = float(value_str)
                        if value == value:  # Not NaN
                            values.append(value * 1000.0)  # Convert to ms
            
            if values:
                return sum(values) / len(values)
        
        return 0.0
    except Exception as e:
        print(f"    Warning: Prometheus query failed for {service_name}: {e}")
        return 0.0


def reset_cluster():
    """Reset all monitored deployments to 1 replica."""
    print("  Resetting all deployments to 1 replica...")
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.patch_namespaced_deployment_scale(
                name=svc,
                namespace=NAMESPACE,
                body={"spec": {"replicas": 1}}
            )
            print(f"    Reset {svc} to 1 replica")
        except Exception as e:
            print(f"    Warning: could not reset {svc}: {e}")
    
    print("  Waiting 2 minutes for pods to stabilize...")
    time.sleep(120)
    print("  Cluster reset complete.")


def enable_proactive():
    """Enable proactive autoscaling system."""
    print("  Enabling proactive condition...")
    
    # Delete HPA resources
    autoscaling_v2 = client.AutoscalingV2Api()
    for svc in MONITORED_SERVICES:
        hpa_name = f"{svc}-hpa"
        try:
            autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(
                name=hpa_name,
                namespace=NAMESPACE
            )
            print(f"    Deleted HPA: {hpa_name}")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"    HPA not found (already deleted): {hpa_name}")
            else:
                print(f"    Warning: could not delete HPA {hpa_name}: {e}")
    
    # Scale controller to 1 replica
    import subprocess
    try:
        result = subprocess.run(
            ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster", 
             "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("    Scaled scaling-controller to 1 replica")
        else:
            print(f"    Warning: could not scale scaling-controller: {result.stderr}")
    except Exception as e:
        print(f"    Warning: could not scale scaling-controller: {e}")
    
    time.sleep(15)
    print("  Proactive system active.")


def enable_reactive():
    """Enable reactive HPA baseline."""
    print("  Enabling reactive condition...")
    
    # Scale controller to 0 replicas
    import subprocess
    try:
        result = subprocess.run(
            ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster", 
             "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=0"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("    Scaled scaling-controller to 0 replicas")
        else:
            print(f"    Warning: could not scale scaling-controller: {result.stderr}")
    except Exception as e:
        print(f"    Warning: could not scale scaling-controller: {e}")
    
    # Apply HPA resources
    hpa_path = Path(__file__).parent.parent / "k8s" / "hpa-baseline.yaml"
    if hpa_path.exists():
        result = subprocess.run(
            ["kubectl", "apply", "-f", str(hpa_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"    Applied HPA baseline")
        else:
            print(f"    Warning: kubectl apply failed: {result.stderr}")
    
    time.sleep(15)
    print("  Reactive HPA baseline active.")


def collect_snapshot(condition: str, interval_idx: int) -> dict:
    """Collect one polling snapshot for all services."""
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "condition": condition,
        "pattern": "no-load",
        "interval_idx": interval_idx,
        "services": {}
    }

    for svc in MONITORED_SERVICES:
        # Query replica count
        try:
            dep = apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            replicas = dep.spec.replicas or 1
        except Exception:
            replicas = -1

        # Query p95 latency
        p95_query = f'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        p95 = query_prometheus_for_service(p95_query, svc)

        # Query CPU utilization
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", pod=~"{svc}.*"}}[1m])) * 100'
        cpu = query_prometheus(cpu_query)

        slo_violated = p95 > SLO_THRESHOLD_MS
        snapshot["services"][svc] = {
            "replicas": replicas,
            "p95_ms": p95,
            "cpu_pct": cpu,
            "slo_violated": slo_violated,
        }

    return snapshot


def run_no_load_test(condition: str):
    """Run a no-load test for the specified condition."""
    print(f"\n{'='*60}")
    print(f"  NO-LOAD TEST: {condition}")
    print(f"{'='*60}")

    # Switch condition
    if condition == "proactive":
        enable_proactive()
    else:
        enable_reactive()

    reset_cluster()

    out_path = RESULTS_DIR / f"{condition}_no-load_test.jsonl"
    snapshots = []

    print(f"  NO LOAD - Just collecting metrics for 10 minutes...")

    # Collect for 10 minutes = 20 intervals at 30s each
    n_intervals = 20
    for i in range(n_intervals):
        time.sleep(POLL_INTERVAL_S)
        snap = collect_snapshot(condition, i)
        snapshots.append(snap)

        # Live SLO violation indicator
        violations = [
            svc for svc, m in snap["services"].items()
            if m["slo_violated"]
        ]
        rep_str = " ".join(
            f"{s}={snap['services'][s]['replicas']}"
            for s in MONITORED_SERVICES
        )
        print(f"  [{i+1:02d}/{n_intervals}] violations={violations or 'none'} | {rep_str}")

    # Write results
    with open(out_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")

    print(f"  Results saved: {out_path}")
    
    # Summary
    violation_count = sum(1 for s in snapshots if any(m['slo_violated'] for m in s['services'].values()))
    print(f"\n  SUMMARY:")
    print(f"  SLO violations: {violation_count}/{n_intervals} intervals ({violation_count/n_intervals*100:.1f}%)")
    
    return out_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run no-load test to check for baseline violations")
    parser.add_argument("--condition", required=True, choices=["proactive", "reactive"],
                       help="Autoscaling condition to test")
    
    args = parser.parse_args()
    
    print("="*60)
    print("NO-LOAD BASELINE TEST")
    print("="*60)
    print(f"Condition: {args.condition}")
    print(f"Duration: 10 minutes (no load generation)")
    print(f"Purpose: Check if SLO violations occur without traffic")
    print("="*60)
    
    run_no_load_test(args.condition)
    
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)


if __name__ == "__main__":
    import sys
    sys.exit(main())
