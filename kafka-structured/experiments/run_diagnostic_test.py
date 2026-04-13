#!/usr/bin/env python3
"""
Diagnostic Test Runner
Runs ONE proactive + ONE reactive step test with comprehensive logging.
Outputs detailed analysis of whether scaling actually reduces violations.
"""

import subprocess
import time
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from kubernetes import client, config

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────
SLO_THRESHOLD_MS = 35.68
NAMESPACE = "sock-shop"
POLL_INTERVAL_S = 30
LOAD_DURATION_MIN = 5       # 5 minutes of load
N_INTERVALS = 10            # 10 intervals × 30s = 5 min of data collection
SETTLE_SECONDS = 30         # 30s settle after load

MONITORED_SERVICES = [
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://34.170.213.190:9090")
LOCUST_VM_IP = os.getenv("LOCUST_VM_IP", "35.222.116.125")
LOCUST_SSH_USER = os.getenv("LOCUST_SSH_USER", "User")
LOCUST_SSH_KEY = os.getenv("LOCUST_SSH_KEY", os.path.expanduser("~/.ssh/google_compute_engine"))
SOCK_SHOP_EXTERNAL_IP = os.getenv("SOCK_SHOP_EXTERNAL_IP", "104.154.246.88")

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────
# K8s setup
# ──────────────────────────────────────────────────────────────────
config.load_kube_config()
apps_v1 = client.AppsV1Api()


# ──────────────────────────────────────────────────────────────────
# Prometheus helpers
# ──────────────────────────────────────────────────────────────────
def query_prometheus(query: str) -> float:
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query}, timeout=5
        )
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            val = data["data"]["result"][0]["value"][1]
            if val in ("NaN", "+Inf", "-Inf"):
                return 0.0
            v = float(val)
            return v if v == v else 0.0
        return 0.0
    except Exception as e:
        print(f"    [WARN] Prometheus query failed: {e}")
        return 0.0


def query_prometheus_for_service(query: str, service_name: str) -> float:
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query}, timeout=5
        )
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            values = []
            for result in data["data"]["result"]:
                metric = result.get("metric", {})
                svc = metric.get("service") or metric.get("job", "")
                if svc == "cart":
                    svc = "carts"
                elif svc == "frontend":
                    svc = "front-end"
                if svc == service_name:
                    val = result["value"][1]
                    if val not in ("NaN", "+Inf", "-Inf"):
                        v = float(val)
                        if v == v:
                            values.append(v * 1000.0)
            if values:
                return sum(values) / len(values)
        return 0.0
    except Exception as e:
        print(f"    [WARN] Prom query failed for {service_name}: {e}")
        return 0.0


# ──────────────────────────────────────────────────────────────────
# Locust
# ──────────────────────────────────────────────────────────────────
def start_locust(pattern: str, duration_min: int):
    locustfile = f"locustfile_{pattern}.py"
    remote_cmd = (
        f"source ~/locust-venv/bin/activate && "
        f"LOCUST_RUN_TIME_MINUTES={duration_min} "
        f"locust -f ~/{locustfile} --headless --run-time {duration_min}m "
        f"--host http://{SOCK_SHOP_EXTERNAL_IP} 2>&1"
    )
    ssh_cmd = [
        "ssh", "-i", LOCUST_SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}",
        remote_cmd
    ]
    print(f"  Starting Locust: {pattern} pattern for {duration_min} min")
    proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc


def stop_locust(proc):
    if proc and proc.poll() is None:
        print("  Stopping Locust...")
        proc.terminate()
        try:
            proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


# ──────────────────────────────────────────────────────────────────
# Cluster management
# ──────────────────────────────────────────────────────────────────
def reset_cluster():
    print("  Resetting all deployments to 1 replica...")
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.patch_namespaced_deployment_scale(
                name=svc, namespace=NAMESPACE,
                body={"spec": {"replicas": 1}}
            )
        except Exception as e:
            print(f"    [WARN] Could not reset {svc}: {e}")
    print("  Waiting 2 min for stabilization...")
    time.sleep(120)
    print("  Cluster reset done.")


def enable_proactive():
    print("  Enabling PROACTIVE: deleting HPAs, scaling controller to 1...")
    autoscaling_v2 = client.AutoscalingV2Api()
    for svc in MONITORED_SERVICES:
        try:
            autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(
                name=f"{svc}-hpa", namespace=NAMESPACE
            )
        except client.exceptions.ApiException as e:
            if e.status != 404:
                print(f"    [WARN] HPA delete failed: {e}")

    subprocess.run(
        ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster",
         "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=1"],
        capture_output=True, text=True, timeout=30
    )
    time.sleep(15)
    print("  Proactive system ACTIVE.")


def enable_reactive():
    print("  Enabling REACTIVE: controller to 0, applying HPAs...")
    subprocess.run(
        ["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster",
         "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=0"],
        capture_output=True, text=True, timeout=30
    )
    hpa_path = Path(__file__).parent.parent / "k8s" / "hpa-baseline.yaml"
    subprocess.run(
        ["kubectl", "apply", "-f", str(hpa_path)],
        capture_output=True, text=True
    )
    time.sleep(15)
    print("  Reactive HPA baseline ACTIVE.")


# ──────────────────────────────────────────────────────────────────
# Snapshot collection
# ──────────────────────────────────────────────────────────────────
def collect_snapshot(condition, pattern, run_id, interval_idx):
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "condition": condition,
        "pattern": pattern,
        "interval_idx": interval_idx,
        "services": {}
    }

    for svc in MONITORED_SERVICES:
        try:
            dep = apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            replicas = dep.spec.replicas or 1
        except Exception:
            replicas = -1

        p95_query = 'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        p95 = query_prometheus_for_service(p95_query, svc)

        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", pod=~"{svc}.*"}}[1m])) * 100'
        cpu = query_prometheus(cpu_query)

        # Also collect p99 and request rate for more data
        p99_query = 'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        p99 = query_prometheus_for_service(p99_query, svc)

        rps_query = 'sum(rate(request_duration_seconds_count[1m])) by (job, service, instance)'
        rps = query_prometheus_for_service(rps_query, svc)
        # RPS is already in req/s (not ms), undo the ×1000 from the helper
        rps = rps / 1000.0 if rps > 0 else 0.0

        snapshot["services"][svc] = {
            "replicas": replicas,
            "p95_ms": p95,
            "p99_ms": p99,
            "cpu_pct": cpu,
            "rps": rps,
            "slo_violated": p95 > SLO_THRESHOLD_MS,
        }

    return snapshot


# ──────────────────────────────────────────────────────────────────
# Run single experiment
# ──────────────────────────────────────────────────────────────────
def run_experiment(condition: str, pattern: str, run_id: int) -> list:
    label = f"diag_{condition}_{pattern}_run{run_id:02d}"
    print(f"\n{'='*70}")
    print(f"  DIAGNOSTIC RUN: {label}")
    print(f"  Duration: {LOAD_DURATION_MIN}m load + {SETTLE_SECONDS//60}m settle")
    print(f"  Intervals: {N_INTERVALS} × {POLL_INTERVAL_S}s = {N_INTERVALS * POLL_INTERVAL_S // 60}m")
    print(f"{'='*70}")

    if condition == "proactive":
        enable_proactive()
    else:
        enable_reactive()

    reset_cluster()

    # Start load
    load_proc = start_locust(pattern, LOAD_DURATION_MIN)
    print(f"  Load started. Collecting {N_INTERVALS} snapshots...\n")

    snapshots = []
    header = f"  {'idx':>3} | {'time':>8} | "
    for svc in ["front-end", "carts", "orders"]:
        header += f"{svc:>12} (rep/p95/cpu) | "
    print(header)
    print("  " + "-" * (len(header) - 2))

    start_time = time.time()
    for i in range(N_INTERVALS):
        target_time = start_time + (i + 1) * POLL_INTERVAL_S
        sleep_duration = target_time - time.time()
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        snap = collect_snapshot(condition, pattern, run_id, i)
        snapshots.append(snap)

        # Check locust still running
        if load_proc.poll() is not None and i < N_INTERVALS - 2:
            print(f"  [WARN] Locust exited early at interval {i}!")

        # Print live status (compact)
        elapsed_min = (i + 1) * POLL_INTERVAL_S / 60
        row = f"  {i:3d} | {elapsed_min:5.1f}m | "
        for svc in ["front-end", "carts", "orders"]:
            s = snap["services"][svc]
            viol = "!" if s["slo_violated"] else " "
            row += f"  {s['replicas']}r {s['p95_ms']:7.1f}ms {s['cpu_pct']:5.1f}%{viol}| "
        print(row)

    # Stop load
    stop_locust(load_proc)

    # Settle period - also collect a few snapshots
    print(f"\n  Load stopped. Collecting settle snapshots ({SETTLE_SECONDS//30} intervals)...")
    for i in range(SETTLE_SECONDS // 30):
        time.sleep(30)
        snap = collect_snapshot(condition, pattern, run_id, N_INTERVALS + i)
        snap["phase"] = "settle"
        snapshots.append(snap)

    # Save results
    out_path = RESULTS_DIR / f"{label}.jsonl"
    with open(out_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")
    print(f"  Results saved: {out_path}")

    return snapshots


# ──────────────────────────────────────────────────────────────────
# Analysis
# ──────────────────────────────────────────────────────────────────
def analyze_run(snapshots: list, label: str):
    """Analyze a single run's data."""
    print(f"\n{'='*70}")
    print(f"  ANALYSIS: {label}")
    print(f"{'='*70}")

    # Only load phase snapshots
    load_snaps = [s for s in snapshots if s.get("phase") != "settle"]

    for svc in MONITORED_SERVICES:
        entries = []
        for snap in load_snaps:
            s = snap["services"][svc]
            entries.append(s)

        # Basic stats
        total = len(entries)
        violations = sum(1 for e in entries if e["slo_violated"])
        p95_values = [e["p95_ms"] for e in entries if e["p95_ms"] > 0]
        replicas_over_time = [e["replicas"] for e in entries]

        # Scaling happened?
        max_rep = max(replicas_over_time) if replicas_over_time else 1
        scaled = max_rep > 1

        # Group p95 by replica count
        p95_by_rep = {}
        for e in entries:
            r = e["replicas"]
            if e["p95_ms"] > 0:
                p95_by_rep.setdefault(r, []).append(e["p95_ms"])

        # Time to first scale
        first_scale_idx = None
        for idx, e in enumerate(entries):
            if e["replicas"] > 1:
                first_scale_idx = idx
                break

        # Time to first violation
        first_viol_idx = None
        for idx, e in enumerate(entries):
            if e["slo_violated"]:
                first_viol_idx = idx
                break

        viol_rate = (violations / total * 100) if total > 0 else 0
        avg_p95 = sum(p95_values) / len(p95_values) if p95_values else 0
        max_p95 = max(p95_values) if p95_values else 0

        print(f"\n  {svc}:")
        print(f"    Violations:     {violations}/{total} ({viol_rate:.1f}%)")
        print(f"    Avg p95 (>0):   {avg_p95:.1f}ms")
        print(f"    Max p95:        {max_p95:.1f}ms")
        print(f"    Max replicas:   {max_rep}")
        print(f"    Scaled:         {'YES' if scaled else 'NO'}")
        if first_scale_idx is not None:
            print(f"    First scale at: interval {first_scale_idx} ({first_scale_idx * 30}s)")
        if first_viol_idx is not None:
            print(f"    First viol at:  interval {first_viol_idx} ({first_viol_idx * 30}s)")

        if scaled and first_scale_idx is not None and first_viol_idx is not None:
            lead_time = (first_viol_idx - first_scale_idx) * 30
            if lead_time > 0:
                print(f"    Scale BEFORE violation by {lead_time}s (OK)")
            elif lead_time == 0:
                print(f"    Scale SAME interval as violation")
            else:
                print(f"    Scale AFTER violation by {-lead_time}s (FAIL)")

        # Key diagnostic: does more replicas = lower p95?
        if len(p95_by_rep) > 1:
            print(f"    === SCALING EFFECTIVENESS ===")
            for rep in sorted(p95_by_rep):
                vals = p95_by_rep[rep]
                avg = sum(vals) / len(vals)
                print(f"      {rep} replicas: avg p95 = {avg:.1f}ms (n={len(vals)})")

            # Check for DB bottleneck signature
            cpu_values = [e["cpu_pct"] for e in entries if e["slo_violated"]]
            if cpu_values:
                avg_cpu_during_viol = sum(cpu_values) / len(cpu_values)
                if avg_cpu_during_viol < 25:
                    print(f"    ⚠ DB BOTTLENECK SIGNATURE: avg CPU during violations = {avg_cpu_during_viol:.1f}% (low)")
                    print(f"      Pods are WAITING on DB, not computing. Scaling won't help.")

    # Overall summary
    total_violations = sum(
        1 for snap in load_snaps
        for svc in MONITORED_SERVICES
        if snap["services"][svc]["slo_violated"]
    )
    total_checks = len(load_snaps) * len(MONITORED_SERVICES)
    print(f"\n  OVERALL: {total_violations}/{total_checks} service-intervals violated "
          f"({total_violations/total_checks*100:.1f}%)")


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
def main():
    print("="*70)
    print("  DIAGNOSTIC TEST SUITE")
    print(f"  SLO Threshold: {SLO_THRESHOLD_MS}ms")
    print(f"  Load: {LOAD_DURATION_MIN}m step pattern")
    print(f"  Collection: {N_INTERVALS} intervals × {POLL_INTERVAL_S}s")
    print("="*70)

    # Pre-flight checks
    print("\n[PRE-FLIGHT]")
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "up"}, timeout=5)
        print(f"  Prometheus: {'OK' if r.status_code == 200 else 'FAIL'}")
    except Exception as e:
        print(f"  Prometheus: FAIL ({e})")
        return 1

    try:
        ssh_test = subprocess.run(
            ["ssh", "-i", LOCUST_SSH_KEY, "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=15",
             f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}", "echo OK"],
            capture_output=True, text=True, timeout=25
        )
        print(f"  Locust VM:  {'OK' if ssh_test.returncode == 0 else 'FAIL'}")
        if ssh_test.returncode != 0:
            print(f"    stderr: {ssh_test.stderr[:200]}")
            return 1
    except Exception as e:
        print(f"  Locust VM:  FAIL ({e})")
        return 1

    # Log current DB state
    print("\n[CURRENT DATABASE STATE]")
    for db in ["carts-db", "orders-db", "catalogue-db", "user-db", "session-db"]:
        try:
            dep = apps_v1.read_namespaced_deployment(name=db, namespace=NAMESPACE)
            print(f"  {db}: {dep.spec.replicas} replicas")
        except Exception:
            print(f"  {db}: not found")

    # Run 1: PROACTIVE
    print("\n" + "="*70)
    print("  PHASE 1/2: PROACTIVE TEST")
    print("="*70)
    proactive_snaps = run_experiment("proactive", "step", 2001)

    # Run 2: REACTIVE
    print("\n" + "="*70)
    print("  PHASE 2/2: REACTIVE TEST")
    print("="*70)
    reactive_snaps = run_experiment("reactive", "step", 2001)

    # Analysis
    print("\n" + "#"*70)
    print("  FINAL ANALYSIS")
    print("#"*70)

    analyze_run(proactive_snaps, "PROACTIVE step")
    analyze_run(reactive_snaps, "REACTIVE step")

    # Head-to-head comparison
    print(f"\n{'='*70}")
    print("  HEAD-TO-HEAD COMPARISON")
    print(f"{'='*70}")

    pro_load = [s for s in proactive_snaps if s.get("phase") != "settle"]
    rea_load = [s for s in reactive_snaps if s.get("phase") != "settle"]

    print(f"\n  {'Service':<12} | {'Proactive VR%':>14} | {'Reactive VR%':>14} | {'Pro avg p95':>12} | {'Rea avg p95':>12} | {'Winner':>8}")
    print("  " + "-" * 85)
    for svc in MONITORED_SERVICES:
        pro_viol = sum(1 for s in pro_load if s["services"][svc]["slo_violated"])
        rea_viol = sum(1 for s in rea_load if s["services"][svc]["slo_violated"])
        pro_vr = pro_viol / len(pro_load) * 100
        rea_vr = rea_viol / len(rea_load) * 100

        pro_p95 = [s["services"][svc]["p95_ms"] for s in pro_load if s["services"][svc]["p95_ms"] > 0]
        rea_p95 = [s["services"][svc]["p95_ms"] for s in rea_load if s["services"][svc]["p95_ms"] > 0]
        pro_avg = sum(pro_p95)/len(pro_p95) if pro_p95 else 0
        rea_avg = sum(rea_p95)/len(rea_p95) if rea_p95 else 0

        winner = "TIE"
        if pro_vr < rea_vr:
            winner = "PRO (W)"
        elif rea_vr < pro_vr:
            winner = "REA (W)"

        print(f"  {svc:<12} | {pro_vr:13.1f}% | {rea_vr:13.1f}% | {pro_avg:10.1f}ms | {rea_avg:10.1f}ms | {winner:>8}")

    # Overall
    pro_total_viol = sum(1 for s in pro_load for svc in MONITORED_SERVICES if s["services"][svc]["slo_violated"])
    rea_total_viol = sum(1 for s in rea_load for svc in MONITORED_SERVICES if s["services"][svc]["slo_violated"])
    pro_total = len(pro_load) * len(MONITORED_SERVICES)
    rea_total = len(rea_load) * len(MONITORED_SERVICES)
    print(f"\n  TOTAL:  Proactive {pro_total_viol}/{pro_total} ({pro_total_viol/pro_total*100:.1f}%)  "
          f"vs  Reactive {rea_total_viol}/{rea_total} ({rea_total_viol/rea_total*100:.1f}%)")

    print(f"\n  Results saved to:")
    print(f"    {RESULTS_DIR}/diag_proactive_step_run2001.jsonl")
    print(f"    {RESULTS_DIR}/diag_reactive_step_run2001.jsonl")
    print(f"\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
