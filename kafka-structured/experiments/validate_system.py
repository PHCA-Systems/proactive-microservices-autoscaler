#!/usr/bin/env python3
"""
System Validation Script
Comprehensive validation of proactive autoscaling system before experiments
"""

import subprocess
import time
import json
import requests
from kubernetes import client, config

# Configuration
PROMETHEUS_URL = "http://34.170.213.190:9090"
SOCK_SHOP_NAMESPACE = "sock-shop"
KAFKA_NAMESPACE = "kafka"
PIPELINE_CONTEXT = "gke_grad-phca_us-central1-a_pipeline-cluster"
SOCK_SHOP_CONTEXT = "gke_grad-phca_us-central1-a_sock-shop-cluster"
MONITORED_SERVICES = ["front-end", "carts", "orders", "catalogue", "user", "payment", "shipping"]

def run_kubectl(context, args):
    """Run kubectl command and return (success, output)"""
    cmd = ["kubectl", f"--context={context}"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def check_kafka_topics():
    """Check if Kafka topics exist"""
    print("\n" + "="*80)
    print("CHECKING KAFKA TOPICS")
    print("="*80)
    
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["exec", "-n", KAFKA_NAMESPACE, "kafka-0", "--",
         "kafka-topics.sh", "--bootstrap-server", "localhost:9092", "--list"]
    )
    
    if success:
        topics = output.strip().split('\n')
        required = ["metrics", "model-votes", "scaling-decisions"]
        for topic in required:
            if topic in topics:
                print(f"  ✓ Topic '{topic}' exists")
            else:
                print(f"  ✗ Topic '{topic}' MISSING")
                return False
        return True
    else:
        print(f"  ✗ Failed to list topics: {output}")
        return False

def check_ml_models_voting():
    """Check if ML models are voting"""
    print("\n" + "="*80)
    print("CHECKING ML MODEL VOTES")
    print("="*80)
    
    # Check authoritative-scaler logs for recent votes
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["logs", "-n", KAFKA_NAMESPACE, "deployment/authoritative-scaler", "--tail=50"]
    )
    
    if success:
        if "logistic_regression" in output and "xgboost" in output and "random_forest" in output:
            print("  ✓ All 3 ML models are voting")
            
            # Extract a recent decision
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if "DECISION:" in line:
                    print(f"\n  Recent decision:")
                    for j in range(max(0, i-5), min(len(lines), i+3)):
                        print(f"    {lines[j]}")
                    break
            return True
        else:
            print("  ✗ Not all ML models are voting")
            print(f"  Output: {output[:500]}")
            return False
    else:
        print(f"  ✗ Failed to get logs: {output}")
        return False

def check_scaling_controller():
    """Check if scaling controller is receiving decisions"""
    print("\n" + "="*80)
    print("CHECKING SCALING CONTROLLER")
    print("="*80)
    
    # Check if pod is running
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["get", "pods", "-n", KAFKA_NAMESPACE, "-l", "app=scaling-controller"]
    )
    
    if not success or "Running" not in output:
        print(f"  ✗ Scaling controller pod not running")
        print(f"  Output: {output}")
        return False
    
    print("  ✓ Scaling controller pod is running")
    
    # Check logs for decisions
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["logs", "-n", KAFKA_NAMESPACE, "deployment/scaling-controller", "--tail=30"]
    )
    
    if success:
        if "[DECISION] Received:" in output:
            print("  ✓ Scaling controller is receiving decisions from Kafka")
            
            # Count recent decisions
            decision_count = output.count("[DECISION] Received:")
            print(f"  ✓ Received {decision_count} decisions in last 30 log lines")
            return True
        else:
            print("  ✗ No decisions found in logs")
            print(f"  Output: {output[:500]}")
            return False
    else:
        print(f"  ✗ Failed to get logs: {output}")
        return False

def test_kubectl_scaling():
    """Test if kubectl can scale deployments from inside the controller pod"""
    print("\n" + "="*80)
    print("TESTING KUBECTL SCALING CAPABILITY")
    print("="*80)
    
    # Get current replicas
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["exec", "-n", KAFKA_NAMESPACE, "deployment/scaling-controller", "--",
         "kubectl", "--context=sock-shop-cluster", "get", "deployment", "front-end",
         "-n", SOCK_SHOP_NAMESPACE, "-o", "jsonpath={.spec.replicas}"]
    )
    
    if not success:
        print(f"  ✗ Cannot get replica count: {output}")
        return False
    
    current_replicas = int(output.strip())
    print(f"  ✓ Current front-end replicas: {current_replicas}")
    
    # Test scaling up
    test_replicas = current_replicas + 1
    print(f"  Testing scale to {test_replicas}...")
    
    success, output = run_kubectl(
        PIPELINE_CONTEXT,
        ["exec", "-n", KAFKA_NAMESPACE, "deployment/scaling-controller", "--",
         "kubectl", "--context=sock-shop-cluster", "scale", "deployment", "front-end",
         "-n", SOCK_SHOP_NAMESPACE, f"--replicas={test_replicas}"]
    )
    
    if not success:
        print(f"  ✗ Scaling failed: {output}")
        return False
    
    print(f"  ✓ Scaling command succeeded")
    
    # Wait and verify
    time.sleep(5)
    
    success, output = run_kubectl(
        SOCK_SHOP_CONTEXT,
        ["get", "deployment", "front-end", "-n", SOCK_SHOP_NAMESPACE,
         "-o", "jsonpath={.spec.replicas}"]
    )
    
    if success:
        new_replicas = int(output.strip())
        if new_replicas == test_replicas:
            print(f"  ✓ Verified: front-end scaled to {new_replicas}")
            
            # Scale back
            print(f"  Scaling back to {current_replicas}...")
            run_kubectl(
                SOCK_SHOP_CONTEXT,
                ["scale", "deployment", "front-end", "-n", SOCK_SHOP_NAMESPACE,
                 f"--replicas={current_replicas}"]
            )
            return True
        else:
            print(f"  ✗ Replica count mismatch: expected {test_replicas}, got {new_replicas}")
            return False
    else:
        print(f"  ✗ Failed to verify: {output}")
        return False

def check_prometheus():
    """Check Prometheus connectivity and queries"""
    print("\n" + "="*80)
    print("CHECKING PROMETHEUS")
    print("="*80)
    
    try:
        # Test basic connectivity
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "up"}, timeout=5)
        if response.status_code != 200:
            print(f"  ✗ Prometheus returned status {response.status_code}")
            return False
        
        print(f"  ✓ Prometheus accessible at {PROMETHEUS_URL}")
        
        # Test p95 latency query
        query = 'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success" and data["data"]["result"]:
                print(f"  ✓ p95 latency query working ({len(data['data']['result'])} results)")
                
                # Show sample results
                for result in data["data"]["result"][:3]:
                    metric = result.get("metric", {})
                    svc = metric.get("service") or metric.get("job", "unknown")
                    value = float(result["value"][1]) * 1000  # Convert to ms
                    print(f"    {svc}: {value:.2f}ms")
                return True
            else:
                print(f"  ⚠ Query returned no results (expected if no traffic)")
                return True
        else:
            print(f"  ✗ Query failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def check_all_services():
    """Check if all monitored services are running"""
    print("\n" + "="*80)
    print("CHECKING MONITORED SERVICES")
    print("="*80)
    
    config.load_kube_config(context=SOCK_SHOP_CONTEXT)
    apps_v1 = client.AppsV1Api()
    
    all_ok = True
    for svc in MONITORED_SERVICES:
        try:
            dep = apps_v1.read_namespaced_deployment(name=svc, namespace=SOCK_SHOP_NAMESPACE)
            replicas = dep.spec.replicas
            available = dep.status.available_replicas or 0
            
            if available >= replicas:
                print(f"  ✓ {svc:15s} {replicas} replica(s), {available} available")
            else:
                print(f"  ⚠ {svc:15s} {replicas} replica(s), only {available} available")
                all_ok = False
        except Exception as e:
            print(f"  ✗ {svc:15s} Error: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Run all validation checks"""
    print("="*80)
    print("PROACTIVE AUTOSCALER SYSTEM VALIDATION")
    print("="*80)
    
    checks = [
        ("Monitored Services", check_all_services),
        ("Prometheus", check_prometheus),
        ("Kafka Topics", check_kafka_topics),
        ("ML Model Votes", check_ml_models_voting),
        ("Scaling Controller", check_scaling_controller),
        ("kubectl Scaling", test_kubectl_scaling),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n  ✗ Exception during {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:8s} {name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL CHECKS PASSED - System ready for experiments")
        print("="*80)
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Fix issues before running experiments")
        print("="*80)
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
