#!/usr/bin/env python3
"""
Test scale-down logic for Task 4.2
Tests scale-down policy with rolling window evaluation
"""

import sys
import os
from datetime import datetime, timedelta

# Add services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'scaling-controller'))

# Mock the kubernetes and kafka modules before importing controller
from unittest.mock import MagicMock, patch
sys.modules['kubernetes'] = MagicMock()
sys.modules['kubernetes.client'] = MagicMock()
sys.modules['kubernetes.client.rest'] = MagicMock()
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()

# Now import controller
import controller


def test_scaledown_conditions_met():
    """Test scale-down when all conditions are met for 10 consecutive intervals."""
    print("\n" + "="*80)
    print("TEST: Scale-Down with All Conditions Met")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 5  # Current replicas
    mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 10 consecutive intervals with low CPU and latency
    # CPU < 30%, p95 < 0.7 × 36ms = 25.2ms
    for i in range(10):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,  # Below 30%
            "p95_latency_ms": 20.0,  # Below 25.2ms
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was executed
    assert mock_apps_v1.patch_namespaced_deployment_scale.called
    call_args = mock_apps_v1.patch_namespaced_deployment_scale.call_args
    assert call_args[1]['name'] == 'front-end'
    assert call_args[1]['body']['spec']['replicas'] == 4  # 5 - 1
    
    print("✓ Scale-down executed when all conditions met for 10 intervals")
    print(f"  - CPU: 25% < 30% threshold")
    print(f"  - p95: 20ms < 25.2ms threshold (0.7 × 36ms)")
    print(f"  - Replicas: 5 → 4")
    print("="*80)


def test_scaledown_insufficient_window():
    """Test that scale-down does not occur with fewer than 10 intervals."""
    print("\n" + "="*80)
    print("TEST: Scale-Down with Insufficient Window")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add only 9 intervals (not enough)
    for i in range(9):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was NOT executed
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly skipped with only 9 intervals (need 10)")
    print("="*80)


def test_scaledown_high_cpu():
    """Test that scale-down does not occur when CPU is above threshold."""
    print("\n" + "="*80)
    print("TEST: Scale-Down with High CPU")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 10 intervals, but with high CPU in one interval
    for i in range(10):
        cpu = 35.0 if i == 5 else 25.0  # One interval above 30%
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": cpu,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was NOT executed
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly skipped when CPU exceeded 30% in one interval")
    print("="*80)


def test_scaledown_high_latency():
    """Test that scale-down does not occur when latency is above threshold."""
    print("\n" + "="*80)
    print("TEST: Scale-Down with High Latency")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 10 intervals, but with high latency in one interval
    for i in range(10):
        latency = 30.0 if i == 7 else 20.0  # One interval above 25.2ms
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": latency,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was NOT executed
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly skipped when p95 latency exceeded threshold in one interval")
    print("="*80)


def test_scaledown_min_replicas():
    """Test that scale-down does not occur when already at MIN_REPLICAS."""
    print("\n" + "="*80)
    print("TEST: Scale-Down at MIN_REPLICAS")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 1  # Already at MIN_REPLICAS
    mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 10 intervals with low CPU and latency
    for i in range(10):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was NOT executed
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly skipped when already at MIN_REPLICAS (1)")
    print("="*80)


def test_scaledown_cooldown():
    """Test that scale-down does not occur during cooldown period."""
    print("\n" + "="*80)
    print("TEST: Scale-Down During Cooldown")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Put service in cooldown (just scaled)
    controller.last_scale_event["front-end"] = datetime.now()
    
    # Add 10 intervals with low CPU and latency
    for i in range(10):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was NOT executed
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly skipped when service is in cooldown period")
    print("="*80)


def test_scaledown_rolling_window():
    """Test that only the last 10 intervals are evaluated."""
    print("\n" + "="*80)
    print("TEST: Scale-Down Rolling Window Evaluation")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 5
    mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 5 intervals with high CPU (should be ignored)
    for i in range(5):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 80.0,  # High CPU
            "p95_latency_ms": 50.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Add 10 intervals with low CPU and latency (these should be evaluated)
    for i in range(5, 15):
        controller.recent_metrics["front-end"].append({
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down WAS executed (only last 10 intervals matter)
    assert mock_apps_v1.patch_namespaced_deployment_scale.called
    
    print("✓ Scale-down correctly evaluated only the last 10 intervals")
    print("  - First 5 intervals with high CPU were ignored")
    print("  - Last 10 intervals with low CPU/latency triggered scale-down")
    print("="*80)


def test_scaledown_multiple_services():
    """Test that scale-down can occur for multiple services simultaneously."""
    print("\n" + "="*80)
    print("TEST: Scale-Down Multiple Services")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 5
    mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add 10 intervals with low CPU and latency for multiple services
    for service in ["front-end", "carts", "orders"]:
        for i in range(10):
            controller.recent_metrics[service].append({
                "cpu_usage_pct": 25.0,
                "p95_latency_ms": 20.0,
                "timestamp": f"2024-01-01T00:{i:02d}:00Z"
            })
    
    # Execute
    controller.check_scaledown(mock_apps_v1)
    
    # Verify that scale-down was called for all 3 services
    assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == 3
    
    scaled_services = [
        call[1]['name'] 
        for call in mock_apps_v1.patch_namespaced_deployment_scale.call_args_list
    ]
    assert "front-end" in scaled_services
    assert "carts" in scaled_services
    assert "orders" in scaled_services
    
    print("✓ Scale-down correctly executed for multiple services")
    print(f"  - Scaled down: {', '.join(scaled_services)}")
    print("="*80)


def test_metrics_window_maintenance():
    """Test that metrics window is properly maintained (max size)."""
    print("\n" + "="*80)
    print("TEST: Metrics Window Maintenance")
    print("="*80)
    
    # Setup state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    
    # Add more than SCALEDOWN_WINDOW + 5 metrics
    max_size = controller.SCALEDOWN_WINDOW + 5  # 15
    for i in range(20):
        msg = {
            "service": "front-end",
            "cpu_usage_pct": 25.0,
            "p95_latency_ms": 20.0,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z"
        }
        controller.ingest_metric(msg)
    
    # Verify that window size is maintained
    window_size = len(controller.recent_metrics["front-end"])
    assert window_size <= max_size, f"Window size {window_size} exceeds max {max_size}"
    
    print(f"✓ Metrics window correctly maintained at max size {max_size}")
    print(f"  - Added 20 metrics, window size: {window_size}")
    print("="*80)


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("TASK 4.2 SCALE-DOWN LOGIC TESTS")
    print("="*80)
    
    try:
        test_scaledown_conditions_met()
        test_scaledown_insufficient_window()
        test_scaledown_high_cpu()
        test_scaledown_high_latency()
        test_scaledown_min_replicas()
        test_scaledown_cooldown()
        test_scaledown_rolling_window()
        test_scaledown_multiple_services()
        test_metrics_window_maintenance()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
