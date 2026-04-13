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
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://34.170.213.190:9090")

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
            stdout, _ = proc.communicate(timeout=30)
            # Print last 500 chars of output for debugging
            if stdout:
                print(f"  Locust output (last 500 chars): ...{stdout[-500:]}")
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
            value_str = data["data"]["result"][0]["value"][1]
            # Handle NaN values from Prometheus
            if value_str == "NaN" or value_str == "+Inf" or value_str == "-Inf":
                return 0.0
            value = float(value_str)
            # Check if the value is NaN after conversion
            if value != value:  # NaN != NaN is True
                return 0.0
            return value
        return 0.0
    except Exception as e:
        print(f"    Warning: Prometheus query failed: {e}")
        return 0.0


def query_prometheus_for_service(query: str, service_name: str) -> float:
    """
    Query Prometheus and extract value for a specific service.
    Matches the approach used in training data collection.
    Returns 0.0 if query fails or service not found.
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
            # Find results matching the service name
            # Check both 'service' and 'job' labels (Sock Shop uses both)
            values = []
            for result in data["data"]["result"]:
                metric = result.get("metric", {})
                svc = metric.get("service") or metric.get("job", "")
                
                # Normalize job names to service names
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
            
            # Average if multiple instances
            if values:
                return sum(values) / len(values)
        
        return 0.0
    except Exception as e:
        print(f"    Warning: Prometheus query failed for {service_name}: {e}")
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
    
    # Scale controller to 1 replica (in pipeline-cluster kafka namespace)
    try:
        result = subprocess.run(
            ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster", 
             "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("    Scaled scaling-controller to 1 replica in pipeline-cluster")
        else:
            print(f"    Warning: could not scale scaling-controller: {result.stderr}")
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
    
    # Scale controller to 0 replicas (in pipeline-cluster kafka namespace)
    try:
        result = subprocess.run(
            ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster", 
             "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=0"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("    Scaled scaling-controller to 0 replicas in pipeline-cluster")
        else:
            print(f"    Warning: could not scale scaling-controller: {result.stderr}")
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
        # Query all services and filter by service/job label in the result
        # This matches the approach used in training data collection
        p95_query = f'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        p95 = query_prometheus_for_service(p95_query, svc)

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


def execute_run(run: ExperimentRun, run_idx: int = 0, total_runs: int = 0) -> Path:
    """Execute a single experimental run with rich logging."""
    label = f"{run.condition}_{run.pattern}_run{run.run_id:02d}"
    run_start = datetime.now()
    
    print(f"\n{'#'*70}")
    print(f"#  RUN {run_idx}/{total_runs}: {label}")
    print(f"#  Started: {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"#  Condition: {run.condition.upper()} | Pattern: {run.pattern} | Rep: {run.run_id}")
    print(f"{'#'*70}")

    # Switch condition
    print(f"  [SETUP] Switching to {run.condition.upper()} mode...")
    if run.condition == "proactive":
        enable_proactive()
    else:
        enable_reactive()

    print(f"  [SETUP] Resetting cluster to 1 replica each...")
    reset_cluster()

    out_path = RESULTS_DIR / f"{label}.jsonl"
    snapshots = []

    # Start load generator on remote VM
    LOAD_DURATION_MIN = 10
    n_intervals = LOAD_DURATION_MIN * 2
    load_proc = start_locust(run.pattern, duration_min=LOAD_DURATION_MIN)
    
    print(f"  [LOAD] Locust started: {run.pattern} pattern, {LOAD_DURATION_MIN}min, {n_intervals} intervals")
    print(f"  [DATA] Collecting {n_intervals} snapshots at 30s intervals...")
    print(f"")
    print(f"  {'idx':>4} | {'time':>5} | {'FE rep':>6} {'FE p95':>8} | {'cart rep':>8} {'cart p95':>9} | {'ord rep':>7} {'ord p95':>8} | {'viols':>5}")
    print(f"  {'-'*80}")

    start_time = time.time()
    for i in range(n_intervals):
        target_time = start_time + (i + 1) * POLL_INTERVAL_S
        sleep_duration = target_time - time.time()
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        snap = collect_snapshot(run, i)
        snapshots.append(snap)

        # Check if Locust process is still running
        if load_proc.poll() is not None:
            stdout, _ = load_proc.communicate()
            print(f"  *** WARNING: Locust exited early! Output: {stdout[:300]}")
        
        # Rich per-interval logging
        fe = snap["services"]["front-end"]
        ca = snap["services"]["carts"]
        od = snap["services"]["orders"]
        n_viols = sum(1 for s, m in snap["services"].items() if m["slo_violated"])
        v_mark = f"{n_viols}/7" if n_viols > 0 else "0"
        fe_v = "!" if fe["slo_violated"] else " "
        ca_v = "!" if ca["slo_violated"] else " "
        od_v = "!" if od["slo_violated"] else " "
        print(f"  {i+1:>4} | {(i+1)*0.5:>4.1f}m | {fe['replicas']:>5}r {fe['p95_ms']:>6.1f}ms{fe_v}| {ca['replicas']:>7}r {ca['p95_ms']:>7.1f}ms{ca_v}| {od['replicas']:>6}r {od['p95_ms']:>6.1f}ms{od_v}| {v_mark:>5}")

    # Stop load generator
    stop_locust(load_proc)
    elapsed_load = time.time() - start_time
    print(f"")
    print(f"  [LOAD] Stopped after {elapsed_load:.0f}s. Settling 2 minutes...")
    time.sleep(120)

    # Write results
    with open(out_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")

    run_end = datetime.now()
    run_duration = (run_end - run_start).total_seconds() / 60
    total_viols = sum(
        1 for snap in snapshots
        for svc, m in snap["services"].items()
        if m["slo_violated"]
    )
    total_possible = len(snapshots) * len(MONITORED_SERVICES)
    viol_rate = total_viols / total_possible * 100 if total_possible else 0

    print(f"  [DONE] {label} completed in {run_duration:.1f} min")
    print(f"  [DONE] Violation rate: {viol_rate:.1f}% ({total_viols}/{total_possible})")
    print(f"  [DONE] Saved: {out_path}")
    return out_path


def main():
    """Main entry point."""
    suite_start = datetime.now()
    
    print("="*70)
    print(f"  EXPERIMENT SUITE STARTED: {suite_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # --- Validation ---
    print("\n[VALIDATION] Checking infrastructure...")
    validation_passed = True
    
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            print(f"  OK {svc}")
        except Exception as e:
            print(f"  FAIL {svc}: {e}")
            validation_passed = False
    
    # Check scaling controller (try both names)
    print("\n[VALIDATION] Checking scaling controller...")
    controller_found = False
    for ctrl_name in ["scaling-controller", "authoritative-scaler"]:
        try:
            pipeline_config = config.new_client_from_config(context="gke_grad-phca_us-central1-a_pipeline-cluster")
            pipeline_apps_v1 = client.AppsV1Api(api_client=pipeline_config)
            pipeline_apps_v1.read_namespaced_deployment(name=ctrl_name, namespace="kafka")
            print(f"  OK {ctrl_name} found in pipeline-cluster")
            controller_found = True
            break
        except Exception:
            continue
    if not controller_found:
        print(f"  WARNING: No controller deployment found (checked scaling-controller, authoritative-scaler)")
        # Don't fail - controller might be named differently
    
    # Check Prometheus
    print("\n[VALIDATION] Checking Prometheus...")
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "up"}, timeout=5)
        print(f"  OK Prometheus at {PROMETHEUS_URL}" if response.status_code == 200 else f"  FAIL status={response.status_code}")
        if response.status_code != 200:
            validation_passed = False
    except Exception as e:
        print(f"  FAIL Prometheus: {e}")
        validation_passed = False
    
    # Check Locust
    print("\n[VALIDATION] Checking Locust VM...")
    try:
        result = subprocess.run([
            "ssh", "-i", LOCUST_SSH_KEY, "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}", "echo OK"
        ], capture_output=True, text=True, timeout=20)
        print(f"  OK Locust VM at {LOCUST_VM_IP}" if result.returncode == 0 else f"  WARNING: SSH issue (will retry): {result.stderr[:100]}")
    except Exception as e:
        print(f"  WARNING: Locust VM: {e}")
    
    if not validation_passed:
        print("\n*** VALIDATION FAILED - fix issues above ***")
        return 1
    
    print("\n[VALIDATION] ALL CHECKS PASSED")
    
    # --- Schedule ---
    schedule = generate_run_schedule()
    total = len(schedule)
    est_hours = total * 10 / 60  # ~10 min per run
    est_end = suite_start + __import__('datetime').timedelta(minutes=total * 10)
    
    print(f"\n{'='*70}")
    print(f"  SCHEDULE: {total} runs")
    print(f"  Estimated duration: {est_hours:.1f} hours")
    print(f"  Estimated completion: {est_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    for i, run in enumerate(schedule, 1):
        print(f"  {i:>3}. {run.condition:10s} {run.pattern:10s} run{run.run_id}")
    
    print(f"\n{'='*70}")
    print(f"  LAUNCHING NOW - NO PAUSE")
    print(f"{'='*70}\n")

    # --- Execute ---
    completed = []
    failed = []
    
    for idx, run in enumerate(schedule, 1):
        elapsed = (datetime.now() - suite_start).total_seconds() / 60
        remaining = (total - idx + 1) * 10
        eta = datetime.now() + __import__('datetime').timedelta(minutes=remaining)
        
        print(f"\n{'*'*70}")
        print(f"*  PROGRESS: {idx}/{total} | Elapsed: {elapsed:.0f}min | ETA: {eta.strftime('%H:%M:%S')}")
        print(f"{'*'*70}")
        
        try:
            out = execute_run(run, run_idx=idx, total_runs=total)
            completed.append(f"{run.condition}_{run.pattern}_run{run.run_id:02d}")
            print(f"\n  >>> COMPLETED {idx}/{total}: {run.condition}_{run.pattern}_run{run.run_id:02d} <<<")
        except Exception as e:
            label = f"{run.condition}_{run.pattern}_run{run.run_id:02d}"
            failed.append(label)
            print(f"\n  !!! ERROR in {label}: {e} !!!")
            import traceback
            traceback.print_exc()
            # Continue with next run

    suite_end = datetime.now()
    suite_duration = (suite_end - suite_start).total_seconds() / 3600
    
    print(f"\n{'='*70}")
    print(f"  EXPERIMENT SUITE FINISHED")
    print(f"  Started:   {suite_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Finished:  {suite_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration:  {suite_duration:.1f} hours")
    print(f"  Succeeded: {len(completed)}/{total}")
    print(f"  Failed:    {len(failed)}/{total}")
    if failed:
        print(f"  Failed runs: {', '.join(failed)}")
    print(f"  Results in: {RESULTS_DIR}")
    print(f"{'='*70}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
