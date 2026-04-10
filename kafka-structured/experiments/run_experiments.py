#!/usr/bin/env python3
"""
Experiment Runner
Automated orchestration of 34 experimental runs
"""

import subprocess
import time
import json
import os
import requests
from datetime import datetime
from pathlib import Path
from kubernetes import client, config
from run_config import (
    ExperimentRun, MONITORED_SERVICES, NAMESPACE,
    POLL_INTERVAL_S, SLO_THRESHOLD_MS, generate_run_schedule
)

config.load_kube_config()
apps_v1 = client.AppsV1Api()

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Prometheus configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-server.sock-shop.svc.cluster.local:9090")

# Locust VM configuration
LOCUST_VM_IP = os.getenv("LOCUST_VM_IP", "35.222.116.125")
LOCUST_SSH_USER = os.getenv("LOCUST_SSH_USER", "User")
LOCUST_SSH_KEY = os.getenv("LOCUST_SSH_KEY", os.path.expanduser("~/.ssh/google_compute_engine"))
SOCK_SHOP_EXTERNAL_IP = os.getenv("SOCK_SHOP_EXTERNAL_IP", "104.154.246.88")


def start_locust(pattern: str, duration_min: int) -> subprocess.Popen:
    """
    Start Locust load generator on remote VM via SSH.
    Returns the subprocess handle.
    """
    locustfile = f"locustfile_{pattern}.py"
    
    # SSH command to run locust on the VM
    # Set LOCUST_RUN_TIME_MINUTES for the LoadTestShape class
    remote_cmd = (
        f"source ~/locust-venv/bin/activate && "
        f"LOCUST_RUN_TIME_MINUTES={duration_min} "
        f"locust -f ~/{locustfile} --headless --run-time {duration_min}m "
        f"--host http://{SOCK_SHOP_EXTERNAL_IP} 2>&1"
    )
    
    ssh_cmd = [
        "ssh",
        "-i", LOCUST_SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}",
        remote_cmd
    ]
    
    print(f"  Starting Locust on VM: {pattern} pattern for {duration_min} minutes")
    proc = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    return proc


def stop_locust(proc: subprocess.Popen):
    """
    Stop the Locust process gracefully.
    """
    if proc and proc.poll() is None:
        print("  Stopping Locust...")
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print("  Force killing Locust...")
            proc.kill()
            proc.wait()


def query_prometheus(query: str) -> float:
    """
    Query Prometheus and return the first result value.
    Returns 0.0 if query fails or returns no data.
    """
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "success" and data["data"]["result"]:
            value = float(data["data"]["result"][0]["value"][1])
            return value
        return 0.0
    except Exception as e:
        print(f"    Warning: Prometheus query failed: {e}")
        return 0.0


def reset_cluster():
    """
    Reset all monitored deployments to 1 replica.
    This ensures a consistent starting state for each experimental run.
    """
    print("  Resetting all deployments to 1 replica...")
    success_count = 0
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.patch_namespaced_deployment_scale(
                name=svc,
                namespace=NAMESPACE,
                body={"spec": {"replicas": 1}}
            )
            print(f"    Reset {svc} to 1 replica")
            success_count += 1
        except Exception as e:
            print(f"    Warning: could not reset {svc}: {e}")
    
    print(f"  Reset {success_count}/{len(MONITORED_SERVICES)} services successfully")
    print("  Waiting 2 minutes for pods to stabilize...")
    time.sleep(120)  # 2 min for pods to stabilize
    print("  Cluster reset complete.")


def enable_proactive():
    """
    Enable proactive autoscaling system.
    - Delete HPA resources for all monitored services
    - Scale scaling-controller deployment to 1 replica
    """
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
    try:
        apps_v1.patch_namespaced_deployment_scale(
            name="scaling-controller",
            namespace=NAMESPACE,
            body={"spec": {"replicas": 1}}
        )
        print("    Scaled scaling-controller to 1 replica")
    except Exception as e:
        print(f"    Warning: could not scale scaling-controller: {e}")
    
    time.sleep(15)  # Allow controller to start
    print("  Proactive system active.")


def enable_reactive():
    """
    Enable reactive HPA baseline.
    - Apply HPA resources for all monitored services
    - Scale scaling-controller deployment to 0 replicas
    """
    print("  Enabling reactive condition...")
    
    # Scale controller to 0 replicas
    try:
        apps_v1.patch_namespaced_deployment_scale(
            name="scaling-controller",
            namespace=NAMESPACE,
            body={"spec": {"replicas": 0}}
        )
        print("    Scaled scaling-controller to 0 replicas")
    except Exception as e:
        print(f"    Warning: could not scale scaling-controller: {e}")
    
    # Apply HPA resources using kubectl (easier than constructing HPA objects)
    hpa_path = Path(__file__).parent.parent / "k8s" / "hpa-baseline.yaml"
    if not hpa_path.exists():
        print(f"    ERROR: HPA baseline file not found at {hpa_path}")
        return
    
    result = subprocess.run(
        ["kubectl", "apply", "-f", str(hpa_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"    Applied HPA baseline from {hpa_path}")
    else:
        print(f"    Warning: kubectl apply failed: {result.stderr}")
    
    time.sleep(15)  # Allow HPA to initialize
    print("  Reactive HPA baseline active.")


def collect_snapshot(run: ExperimentRun, interval_idx: int) -> dict:
    """
    Collect one polling snapshot for all services.
    Queries Kubernetes API for replica counts and Prometheus for metrics.
    """
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "run_id": run.run_id,
        "condition": run.condition,
        "pattern": run.pattern,
        "interval_idx": interval_idx,
        "services": {}
    }

    for svc in MONITORED_SERVICES:
        # Query replica count from Kubernetes
        try:
            dep = apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            replicas = dep.spec.replicas or 1
        except Exception:
            replicas = -1

        # Query p95 latency from Prometheus (in milliseconds)
        # Using histogram_quantile on request_duration_seconds metric
        p95_query = f'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket{{job="{svc}"}}[1m])) by (le)) * 1000'
        p95 = query_prometheus(p95_query)

        # Query CPU utilization from Prometheus (as percentage)
        # Using container_cpu_usage_seconds_total metric
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


def execute_run(run: ExperimentRun) -> Path:
    """Execute a single experimental run."""
    label = f"{run.condition}_{run.pattern}_run{run.run_id:02d}"
    print(f"\n{'='*60}")
    print(f"  RUN: {label}")
    print(f"{'='*60}")

    # Switch condition
    if run.condition == "proactive":
        enable_proactive()
    else:
        enable_reactive()

    reset_cluster()

    out_path = RESULTS_DIR / f"{label}.jsonl"
    snapshots = []

    # Start load generator on remote VM
    # Duration: 12 minutes of load generation
    load_proc = start_locust(run.pattern, duration_min=12)
    
    print(f"  Load generator started (pattern={run.pattern}). Collecting metrics...")

    # Collect for 12 minutes = 24 intervals at 30s each
    n_intervals = 24
    for i in range(n_intervals):
        time.sleep(POLL_INTERVAL_S)
        snap = collect_snapshot(run, i)
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

    # Stop load generator
    stop_locust(load_proc)
    print("  Load generator stopped. Settling 3 minutes...")
    time.sleep(180)

    # Write results
    with open(out_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")

    print(f"  Results saved: {out_path}")
    return out_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run proactive autoscaler experiments")
    parser.add_argument("--pause-before-start", action="store_true",
                       help="Display run schedule and wait for confirmation before starting")
    args = parser.parse_args()
    
    # Validation checks (Task 8.5)
    print("="*60)
    print("EXPERIMENT VALIDATION")
    print("="*60)
    
    validation_passed = True
    
    # Check all 7 service deployments exist
    print("\nChecking service deployments...")
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            print(f"  ✓ {svc}")
        except Exception as e:
            print(f"  ✗ {svc}: {e}")
            validation_passed = False
    
    # Check scaling controller deployment exists
    print("\nChecking scaling controller...")
    try:
        apps_v1.read_namespaced_deployment(name="scaling-controller", namespace=NAMESPACE)
        print(f"  ✓ scaling-controller deployment exists")
    except Exception as e:
        print(f"  ✗ scaling-controller deployment not found: {e}")
        validation_passed = False
    
    # Check Prometheus connectivity
    print("\nChecking Prometheus connectivity...")
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "up"}, timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Prometheus accessible at {PROMETHEUS_URL}")
        else:
            print(f"  ✗ Prometheus returned status {response.status_code}")
            validation_passed = False
    except Exception as e:
        print(f"  ✗ Cannot reach Prometheus: {e}")
        validation_passed = False
    
    # Check Locust VM connectivity
    print("\nChecking Locust VM connectivity...")
    try:
        test_cmd = [
            "ssh",
            "-i", LOCUST_SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}",
            "echo 'OK'"
        ]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✓ Locust VM accessible at {LOCUST_VM_IP}")
        else:
            print(f"  ✗ Cannot SSH to Locust VM: {result.stderr}")
            validation_passed = False
    except Exception as e:
        print(f"  ✗ Cannot reach Locust VM: {e}")
        validation_passed = False
    
    if not validation_passed:
        print("\n✗ VALIDATION FAILED - Please fix the issues above before running experiments")
        return 1
    
    print("\n✓ ALL VALIDATION CHECKS PASSED")
    
    # Generate schedule
    schedule = generate_run_schedule()
    total = len(schedule)
    
    # Pause before start (Task 8.6)
    if args.pause_before_start:
        print(f"\n{'='*60}")
        print("EXPERIMENT SCHEDULE")
        print(f"{'='*60}")
        print(f"Total runs: {total}")
        print(f"Estimated time: {total * 15 / 60:.1f} hours (~{total * 15} minutes)")
        print(f"\nRun breakdown:")
        for pattern, reps in {"constant": 2, "step": 5, "spike": 5, "ramp": 5}.items():
            print(f"  {pattern}: {reps} × 2 conditions = {reps * 2} runs")
        
        print(f"\nFirst 5 runs:")
        for i, run in enumerate(schedule[:5], 1):
            print(f"  {i}. {run.condition:10s} {run.pattern:10s} run {run.run_id}")
        print(f"  ...")
        
        print(f"\n{'='*60}")
        response = input("Press ENTER to start experiments (or Ctrl+C to cancel): ")
        print(f"{'='*60}\n")
    
    print(f"Starting experiment schedule: {total} runs")
    print(f"Estimated time: {total * 15 / 60:.1f} hours\n")

    completed = []
    for idx, run in enumerate(schedule, 1):
        print(f"\nProgress: {idx}/{total}")
        try:
            out = execute_run(run)
            completed.append({"run": run, "output": out, "status": "ok"})
        except Exception as e:
            print(f"  ERROR in run {run}: {e}")
            completed.append({"run": run, "output": None, "status": f"error: {e}"})

    print(f"\n{'='*60}")
    print(f"All runs complete. {sum(1 for c in completed if c['status']=='ok')}/{total} succeeded.")
    print(f"Results in: {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
