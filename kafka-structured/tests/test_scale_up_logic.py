#!/usr/bin/env python3
"""
Test scale-up logic for Task 4.1
Tests bottleneck service selection and scale-up execution
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


def test_bottleneck_selection_with_metrics():
    """Test that bottleneck service is correctly selected based on p95/SLO ratio."""
    print("\n" + "="*80)
    print("TEST: Bottleneck Selection with Metrics")
    print("="*80)
    
    # Setup: Clear state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add metrics for different services
    controller.recent_metrics["front-end"] = [
        {"p95_latency_ms": 40.0, "cpu_usage_pct": 50.0}  # Score: 40/36 = 1.11
    ]
    controller.recent_metrics["carts"] = [
        {"p95_latency_ms": 72.0, "cpu_usage_pct": 60.0}  # Score: 72/36 = 2.0 (HIGHEST)
    ]
    controller.recent_metrics["orders"] = [
        {"p95_latency_ms": 30.0, "cpu_usage_pct": 40.0}  # Score: 30/36 = 0.83
    ]
    
    # Execute
    bottleneck = controller.select_bottleneck_service()
    
    # Verify
    assert bottleneck == "carts", f"Expected 'carts' but got '{bottleneck}'"
    print(f"✓ Correctly selected 'carts' as bottleneck (highest p95/SLO ratio)")
    print("="*80)


def test_bottleneck_selection_with_cooldown():
    """Test that services in cooldown are excluded from bottleneck selection."""
    print("\n" + "="*80)
    print("TEST: Bottleneck Selection with Cooldown")
    print("="*80)
    
    # Setup: Clear state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Add metrics
    controller.recent_metrics["front-end"] = [
        {"p95_latency_ms": 40.0, "cpu_usage_pct": 50.0}  # Score: 1.11
    ]
    controller.recent_metrics["carts"] = [
        {"p95_latency_ms": 72.0, "cpu_usage_pct": 60.0}  # Score: 2.0 (highest but in cooldown)
    ]
    
    # Put carts in cooldown (just scaled)
    controller.last_scale_event["carts"] = datetime.now()
    
    # Execute
    bottleneck = controller.select_bottleneck_service()
    
    # Verify
    assert bottleneck == "front-end", f"Expected 'front-end' but got '{bottleneck}'"
    print(f"✓ Correctly excluded 'carts' (in cooldown) and selected 'front-end'")
    print("="*80)


def test_bottleneck_selection_no_metrics():
    """Test fallback to front-end when no metrics available."""
    print("\n" + "="*80)
    print("TEST: Bottleneck Selection with No Metrics")
    print("="*80)
    
    # Setup: Clear state
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    controller.last_scale_event = {}
    
    # Execute
    bottleneck = controller.select_bottleneck_service()
    
    # Verify
    assert bottleneck == "front-end", f"Expected 'front-end' but got '{bottleneck}'"
    print(f"✓ Correctly fell back to 'front-end' when no metrics available")
    print("="*80)


def test_cooldown_enforcement():
    """Test that cooldown period is correctly enforced."""
    print("\n" + "="*80)
    print("TEST: Cooldown Period Enforcement")
    print("="*80)
    
    # Setup
    controller.last_scale_event = {}
    
    # Test 1: No previous scale event
    assert controller.can_scale("front-end") == True
    print("✓ Service with no previous scale event can scale")
    
    # Test 2: Recent scale event (within cooldown)
    controller.last_scale_event["front-end"] = datetime.now()
    assert controller.can_scale("front-end") == False
    print("✓ Service within cooldown period cannot scale")
    
    # Test 3: Old scale event (outside cooldown)
    controller.last_scale_event["front-end"] = datetime.now() - timedelta(minutes=6)
    assert controller.can_scale("front-end") == True
    print("✓ Service outside cooldown period can scale")
    
    print("="*80)


def test_metrics_ingestion_nested_structure():
    """Test that nested metrics structure is correctly flattened."""
    print("\n" + "="*80)
    print("TEST: Metrics Ingestion with Nested Structure")
    print("="*80)
    
    # Setup
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    
    # Test nested structure (from metrics aggregator)
    nested_msg = {
        "timestamp": "2024-01-01T00:00:00Z",
        "service": "front-end",
        "features": {
            "p95_latency_ms": 45.0,
            "cpu_usage_pct": 55.0,
            "request_rate_rps": 100.0
        }
    }
    
    controller.ingest_metric(nested_msg)
    
    # Verify
    assert len(controller.recent_metrics["front-end"]) == 1
    metric = controller.recent_metrics["front-end"][0]
    assert metric["p95_latency_ms"] == 45.0
    assert metric["cpu_usage_pct"] == 55.0
    assert metric["service"] == "front-end"
    print("✓ Nested metrics structure correctly flattened")
    
    # Test flat structure (for backwards compatibility)
    controller.recent_metrics = {s: [] for s in controller.MONITORED_SERVICES}
    flat_msg = {
        "timestamp": "2024-01-01T00:00:00Z",
        "service": "carts",
        "p95_latency_ms": 50.0,
        "cpu_usage_pct": 60.0
    }
    
    controller.ingest_metric(flat_msg)
    
    # Verify
    assert len(controller.recent_metrics["carts"]) == 1
    metric = controller.recent_metrics["carts"][0]
    assert metric["p95_latency_ms"] == 50.0
    print("✓ Flat metrics structure correctly handled")
    
    print("="*80)


def test_max_replicas_enforcement():
    """Test that MAX_REPLICAS bound is enforced."""
    print("\n" + "="*80)
    print("TEST: MAX_REPLICAS Enforcement")
    print("="*80)
    
    # Setup mock K8s API
    mock_apps_v1 = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 10  # Already at MAX_REPLICAS
    mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
    
    # Setup state
    controller.last_scale_event = {}
    
    # Execute
    controller.handle_scale_up(mock_apps_v1, "front-end")
    
    # Verify that patch was NOT called (already at max)
    assert not mock_apps_v1.patch_namespaced_deployment_scale.called
    print("✓ Scale-up correctly skipped when already at MAX_REPLICAS")
    
    print("="*80)


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("TASK 4.1 SCALE-UP LOGIC TESTS")
    print("="*80)
    
    try:
        test_bottleneck_selection_with_metrics()
        test_bottleneck_selection_with_cooldown()
        test_bottleneck_selection_no_metrics()
        test_cooldown_enforcement()
        test_metrics_ingestion_nested_structure()
        test_max_replicas_enforcement()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
