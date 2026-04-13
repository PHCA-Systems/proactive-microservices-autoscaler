#!/usr/bin/env python3
"""
Quick Validation Test Runner - REACTIVE (HPA)
Runs ONE reactive step test for 5 minutes.
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

SLO_THRESHOLD_MS = 35.68
NAMESPACE = "sock-shop"
POLL_INTERVAL_S = 30
LOAD_DURATION_MIN = 5       # Just 5 minutes of load!
N_INTERVALS = 10            # 10 intervals × 30s = 5 min

MONITORED_SERVICES = ["front-end", "carts", "orders"]

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://34.170.213.190:9090")
LOCUST_VM_IP = os.getenv("LOCUST_VM_IP", "35.222.116.125")
LOCUST_SSH_USER = os.getenv("LOCUST_SSH_USER", "User")
LOCUST_SSH_KEY = os.getenv("LOCUST_SSH_KEY", os.path.expanduser("~/.ssh/google_compute_engine"))
SOCK_SHOP_EXTERNAL_IP = os.getenv("SOCK_SHOP_EXTERNAL_IP", "104.154.246.88")

config.load_kube_config()
apps_v1 = client.AppsV1Api()

def query_prometheus(query: str) -> float:
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            val = data["data"]["result"][0]["value"][1]
            if val in ("NaN", "+Inf", "-Inf"): return 0.0
            return float(val)
        return 0.0
    except: return 0.0

def query_prometheus_for_service(query: str, service_name: str) -> float:
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            values = []
            for result in data["data"]["result"]:
                metric = result.get("metric", {})
                svc = metric.get("service") or metric.get("job", "")
                if svc == "cart": svc = "carts"
                elif svc == "frontend": svc = "front-end"
                if svc == service_name:
                    val = result["value"][1]
                    if val not in ("NaN", "+Inf", "-Inf"):
                        v = float(val)
                        if v == v: values.append(v * 1000.0)
            if values: return sum(values) / len(values)
        return 0.0
    except: return 0.0

def start_locust():
    remote_cmd = (
        f"source ~/locust-venv/bin/activate && "
        f"LOCUST_RUN_TIME_MINUTES=5 "
        f"locust -f ~/locustfile_step.py --headless --run-time 5m "
        f"--host http://{SOCK_SHOP_EXTERNAL_IP} 2>&1"
    )
    ssh_cmd = ["ssh", "-i", LOCUST_SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15", f"{LOCUST_SSH_USER}@{LOCUST_VM_IP}", remote_cmd]
    print(f"  Starting Locust: 5m step pattern")
    return subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def reset_cluster():
    print("  Resetting front-end, carts, orders to 1 replica...")
    for svc in MONITORED_SERVICES:
        apps_v1.patch_namespaced_deployment_scale(name=svc, namespace=NAMESPACE, body={"spec": {"replicas": 1}})
    print("  Waiting 60s for stabilization...")
    time.sleep(60)

def enable_reactive():
    print("  Enabling REACTIVE controller (HPA)...")
    subprocess.run(["kubectl", "--context=gke_grad-phca_us-central1-a_pipeline-cluster", "scale", "deployment", "scaling-controller", "-n", "kafka", "--replicas=0"], capture_output=True)
    hpa_path = Path(__file__).parent.parent / "k8s" / "hpa-baseline.yaml"
    subprocess.run(["kubectl", "--context=gke_grad-phca_us-central1-a_sock-shop-cluster", "apply", "-f", str(hpa_path)], capture_output=True)
    time.sleep(10)

def collect_snapshot(i):
    snap = {"interval": i, "services": {}}
    for svc in MONITORED_SERVICES:
        try:
            dep = apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
            rep = dep.spec.replicas or 1
        except: rep = 1
        p95 = query_prometheus_for_service('histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))', svc)
        cpu = query_prometheus(f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", pod=~"{svc}.*"}}[1m])) * 100')
        snap["services"][svc] = {"replicas": rep, "p95_ms": p95, "cpu_pct": cpu}
    return snap

def main():
    print("\n=== QUICK REACTIVE (HPA) VALIDATION TEST ===")
    enable_reactive()
    reset_cluster()
    
    proc = start_locust()
    
    print("\n  idx |     time |    front-end (rep/p95/cpu) |        carts (rep/p95/cpu) |       orders (rep/p95/cpu) |")
    print("  " + "-"*100)
    
    start_time = time.time()
    for i in range(N_INTERVALS):
        target_time = start_time + (i + 1) * POLL_INTERVAL_S
        sleep_duration = target_time - time.time()
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        snap = collect_snapshot(i)
        
        row = f"  {i:3d} | {(i+1)*30/60:5.1f}m | "
        for svc in ["front-end", "carts", "orders"]:
            s = snap["services"][svc]
            viol = "!" if s["p95_ms"] > SLO_THRESHOLD_MS else " "
            row += f"  {s['replicas']}r {s['p95_ms']:7.1f}ms {s['cpu_pct']:5.1f}%{viol}| "
        print(row)
        
    if proc.poll() is None:
        proc.terminate()
        
    print("============================================\n")

if __name__ == "__main__":
    main()
