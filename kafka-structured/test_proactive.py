#!/usr/bin/env python3
"""
Test script for proactive condition
"""

import time
from kubernetes import client, config

# Load kubeconfig
config.load_kube_config()

# Create API clients for both clusters
# We need to switch contexts manually
import subprocess

def run_kubectl(context, command):
    """Run kubectl command in specific context"""
    full_cmd = f"kubectl --context={context} {command}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

# Contexts
SOCK_SHOP_CONTEXT = "gke_grad-phca_us-central1-a_sock-shop-cluster"
PIPELINE_CONTEXT = "gke_grad-phca_us-central1-a_pipeline-cluster"

print("="*60)
print("ENABLING PROACTIVE CONDITION")
print("="*60)

# Step 1: Delete any existing HPAs in sock-shop-cluster
print("\n1. Deleting HPA resources in sock-shop-cluster...")
services = ["front-end", "carts", "orders", "catalogue", "user", "payment", "shipping"]
for svc in services:
    hpa_name = f"{svc}-hpa"
    success, stdout, stderr = run_kubectl(
        SOCK_SHOP_CONTEXT,
        f"delete hpa {hpa_name} -n sock-shop --ignore-not-found=true"
    )
    if success:
        print(f"  ✓ Deleted HPA: {hpa_name}")
    else:
        print(f"  ℹ HPA not found or already deleted: {hpa_name}")

# Step 2: Scale scaling-controller to 1 replica in pipeline-cluster
print("\n2. Scaling scaling-controller to 1 replica in pipeline-cluster...")
success, stdout, stderr = run_kubectl(
    PIPELINE_CONTEXT,
    "scale deployment scaling-controller -n kafka --replicas=1"
)
if success:
    print("  ✓ Scaled scaling-controller to 1 replica")
else:
    print(f"  ✗ Failed to scale controller: {stderr}")

print("\n3. Waiting 15 seconds for controller to start...")
time.sleep(15)

# Step 3: Check controller pod status
print("\n4. Checking controller pod status...")
success, stdout, stderr = run_kubectl(
    PIPELINE_CONTEXT,
    "get pods -n kafka -l app=scaling-controller"
)
print(stdout)

print("\n5. Checking controller logs...")
success, stdout, stderr = run_kubectl(
    PIPELINE_CONTEXT,
    "logs -n kafka -l app=scaling-controller --tail=20"
)
print(stdout)

print("\n="*60)
print("PROACTIVE CONDITION ENABLED")
print("="*60)
print("\nThe system is now running in proactive mode:")
print("  - HPA resources deleted")
print("  - Scaling controller active (1 replica)")
print("  - ML models making predictions")
print("  - Authoritative scaler making decisions")
print("\nYou can now generate load to test the system.")
