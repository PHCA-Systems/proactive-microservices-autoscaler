#!/usr/bin/env python3
"""
Test script for Task 8.2: Condition Switching
Tests enable_proactive, enable_reactive, and reset_cluster functions
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from kubernetes import client, config
from run_config import MONITORED_SERVICES, NAMESPACE

# Load Kubernetes config
try:
    config.load_kube_config()
except Exception as e:
    print(f"ERROR: Could not load kubeconfig: {e}")
    print("Make sure you're connected to the GKE cluster")
    sys.exit(1)

apps_v1 = client.AppsV1Api()
autoscaling_v2 = client.AutoscalingV2Api()


def check_deployment_replicas(service: str) -> int:
    """Get current replica count for a deployment"""
    try:
        dep = apps_v1.read_namespaced_deployment(name=service, namespace=NAMESPACE)
        return dep.spec.replicas or 0
    except Exception as e:
        print(f"  ERROR: Could not read deployment {service}: {e}")
        return -1


def check_hpa_exists(service: str) -> bool:
    """Check if HPA exists for a service"""
    hpa_name = f"{service}-hpa"
    try:
        autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(
            name=hpa_name,
            namespace=NAMESPACE
        )
        return True
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return False
        else:
            print(f"  WARNING: Error checking HPA {hpa_name}: {e}")
            return False


def check_controller_replicas() -> int:
    """Get current replica count for scaling-controller"""
    try:
        dep = apps_v1.read_namespaced_deployment(
            name="scaling-controller",
            namespace=NAMESPACE
        )
        return dep.spec.replicas or 0
    except Exception as e:
        print(f"  ERROR: Could not read scaling-controller deployment: {e}")
        return -1


def test_reset_cluster():
    """Test reset_cluster function"""
    print("\n" + "="*60)
    print("TEST 1: reset_cluster()")
    print("="*60)
    
    from run_experiments import reset_cluster
    
    print("Before reset:")
    for svc in MONITORED_SERVICES:
        replicas = check_deployment_replicas(svc)
        print(f"  {svc}: {replicas} replicas")
    
    print("\nExecuting reset_cluster()...")
    reset_cluster()
    
    print("\nAfter reset:")
    all_correct = True
    for svc in MONITORED_SERVICES:
        replicas = check_deployment_replicas(svc)
        status = "✓" if replicas == 1 else "✗"
        print(f"  {status} {svc}: {replicas} replicas (expected 1)")
        if replicas != 1:
            all_correct = False
    
    if all_correct:
        print("\n✓ TEST PASSED: All services reset to 1 replica")
        return True
    else:
        print("\n✗ TEST FAILED: Some services not at 1 replica")
        return False


def test_enable_proactive():
    """Test enable_proactive function"""
    print("\n" + "="*60)
    print("TEST 2: enable_proactive()")
    print("="*60)
    
    from run_experiments import enable_proactive
    
    print("Before enabling proactive:")
    controller_replicas = check_controller_replicas()
    print(f"  scaling-controller: {controller_replicas} replicas")
    
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    print(f"  HPAs present: {hpa_count}/{len(MONITORED_SERVICES)}")
    
    print("\nExecuting enable_proactive()...")
    enable_proactive()
    
    print("\nAfter enabling proactive:")
    controller_replicas = check_controller_replicas()
    controller_ok = controller_replicas == 1
    status = "✓" if controller_ok else "✗"
    print(f"  {status} scaling-controller: {controller_replicas} replicas (expected 1)")
    
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    hpa_ok = hpa_count == 0
    status = "✓" if hpa_ok else "✗"
    print(f"  {status} HPAs present: {hpa_count}/{len(MONITORED_SERVICES)} (expected 0)")
    
    if controller_ok and hpa_ok:
        print("\n✓ TEST PASSED: Proactive condition enabled correctly")
        return True
    else:
        print("\n✗ TEST FAILED: Proactive condition not configured correctly")
        return False


def test_enable_reactive():
    """Test enable_reactive function"""
    print("\n" + "="*60)
    print("TEST 3: enable_reactive()")
    print("="*60)
    
    from run_experiments import enable_reactive
    
    print("Before enabling reactive:")
    controller_replicas = check_controller_replicas()
    print(f"  scaling-controller: {controller_replicas} replicas")
    
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    print(f"  HPAs present: {hpa_count}/{len(MONITORED_SERVICES)}")
    
    print("\nExecuting enable_reactive()...")
    enable_reactive()
    
    print("\nAfter enabling reactive:")
    controller_replicas = check_controller_replicas()
    controller_ok = controller_replicas == 0
    status = "✓" if controller_ok else "✗"
    print(f"  {status} scaling-controller: {controller_replicas} replicas (expected 0)")
    
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    hpa_ok = hpa_count == len(MONITORED_SERVICES)
    status = "✓" if hpa_ok else "✗"
    print(f"  {status} HPAs present: {hpa_count}/{len(MONITORED_SERVICES)} (expected {len(MONITORED_SERVICES)})")
    
    if controller_ok and hpa_ok:
        print("\n✓ TEST PASSED: Reactive condition enabled correctly")
        return True
    else:
        print("\n✗ TEST FAILED: Reactive condition not configured correctly")
        return False


def test_condition_switching():
    """Test switching between conditions"""
    print("\n" + "="*60)
    print("TEST 4: Condition Switching (proactive → reactive → proactive)")
    print("="*60)
    
    from run_experiments import enable_proactive, enable_reactive
    
    print("\nStep 1: Enable proactive...")
    enable_proactive()
    controller_replicas = check_controller_replicas()
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    proactive_ok = controller_replicas == 1 and hpa_count == 0
    status = "✓" if proactive_ok else "✗"
    print(f"  {status} Proactive: controller={controller_replicas}, HPAs={hpa_count}")
    
    print("\nStep 2: Switch to reactive...")
    enable_reactive()
    controller_replicas = check_controller_replicas()
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    reactive_ok = controller_replicas == 0 and hpa_count == len(MONITORED_SERVICES)
    status = "✓" if reactive_ok else "✗"
    print(f"  {status} Reactive: controller={controller_replicas}, HPAs={hpa_count}")
    
    print("\nStep 3: Switch back to proactive...")
    enable_proactive()
    controller_replicas = check_controller_replicas()
    hpa_count = sum(1 for svc in MONITORED_SERVICES if check_hpa_exists(svc))
    proactive_ok2 = controller_replicas == 1 and hpa_count == 0
    status = "✓" if proactive_ok2 else "✗"
    print(f"  {status} Proactive: controller={controller_replicas}, HPAs={hpa_count}")
    
    if proactive_ok and reactive_ok and proactive_ok2:
        print("\n✓ TEST PASSED: Condition switching works correctly")
        return True
    else:
        print("\n✗ TEST FAILED: Condition switching has issues")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Task 8.2: Condition Switching Tests")
    print("="*60)
    print(f"Namespace: {NAMESPACE}")
    print(f"Monitored services: {len(MONITORED_SERVICES)}")
    print(f"Services: {', '.join(MONITORED_SERVICES)}")
    
    # Check prerequisites
    print("\nChecking prerequisites...")
    try:
        # Check if namespace exists
        core_v1 = client.CoreV1Api()
        core_v1.read_namespace(NAMESPACE)
        print(f"  ✓ Namespace '{NAMESPACE}' exists")
    except Exception as e:
        print(f"  ✗ ERROR: Namespace '{NAMESPACE}' not found: {e}")
        sys.exit(1)
    
    # Check if scaling-controller deployment exists
    try:
        apps_v1.read_namespaced_deployment(
            name="scaling-controller",
            namespace=NAMESPACE
        )
        print(f"  ✓ scaling-controller deployment exists")
    except Exception as e:
        print(f"  ✗ ERROR: scaling-controller deployment not found: {e}")
        sys.exit(1)
    
    # Check if monitored services exist
    missing_services = []
    for svc in MONITORED_SERVICES:
        try:
            apps_v1.read_namespaced_deployment(name=svc, namespace=NAMESPACE)
        except Exception:
            missing_services.append(svc)
    
    if missing_services:
        print(f"  ✗ ERROR: Missing deployments: {', '.join(missing_services)}")
        sys.exit(1)
    else:
        print(f"  ✓ All {len(MONITORED_SERVICES)} monitored services exist")
    
    # Run tests
    results = []
    results.append(("reset_cluster", test_reset_cluster()))
    results.append(("enable_proactive", test_enable_proactive()))
    results.append(("enable_reactive", test_enable_reactive()))
    results.append(("condition_switching", test_condition_switching()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✓ ALL TESTS PASSED - Task 8.2 implementation verified!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Please review the output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
