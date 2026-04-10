#!/usr/bin/env python3
"""
Test script for condition switching functions (Task 8.2)
Tests enable_proactive, enable_reactive, and reset_cluster functions
"""

import sys
from pathlib import Path

# Add parent directory to path to import from experiments
sys.path.insert(0, str(Path(__file__).parent.parent / "experiments"))

from unittest.mock import Mock, patch, MagicMock, call
from kubernetes import client
import subprocess


def test_reset_cluster():
    """Test reset_cluster function resets all services to 1 replica"""
    print("\n=== Testing reset_cluster ===")
    
    # Import the function
    from run_experiments import reset_cluster, MONITORED_SERVICES, NAMESPACE
    
    # Mock the apps_v1 API
    with patch('run_experiments.apps_v1') as mock_apps_v1, \
         patch('run_experiments.time.sleep'):  # Skip sleep for testing
        
        # Execute
        reset_cluster()
        
        # Verify all services were reset to 1 replica
        assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == len(MONITORED_SERVICES)
        
        for svc in MONITORED_SERVICES:
            mock_apps_v1.patch_namespaced_deployment_scale.assert_any_call(
                name=svc,
                namespace=NAMESPACE,
                body={"spec": {"replicas": 1}}
            )
        
        print("✓ reset_cluster correctly resets all services to 1 replica")


def test_enable_proactive():
    """Test enable_proactive deletes HPAs and scales controller to 1"""
    print("\n=== Testing enable_proactive ===")
    
    from run_experiments import enable_proactive, MONITORED_SERVICES, NAMESPACE
    
    # Mock the Kubernetes clients
    with patch('run_experiments.client.AutoscalingV2Api') as mock_autoscaling_class, \
         patch('run_experiments.apps_v1') as mock_apps_v1, \
         patch('run_experiments.time.sleep'):  # Skip sleep for testing
        
        mock_autoscaling = Mock()
        mock_autoscaling_class.return_value = mock_autoscaling
        
        # Execute
        enable_proactive()
        
        # Verify HPAs were deleted for all services
        assert mock_autoscaling.delete_namespaced_horizontal_pod_autoscaler.call_count == len(MONITORED_SERVICES)
        
        for svc in MONITORED_SERVICES:
            hpa_name = f"{svc}-hpa"
            mock_autoscaling.delete_namespaced_horizontal_pod_autoscaler.assert_any_call(
                name=hpa_name,
                namespace=NAMESPACE
            )
        
        # Verify scaling controller was scaled to 1 replica
        mock_apps_v1.patch_namespaced_deployment_scale.assert_called_once_with(
            name="scaling-controller",
            namespace=NAMESPACE,
            body={"spec": {"replicas": 1}}
        )
        
        print("✓ enable_proactive correctly deletes HPAs and scales controller to 1")


def test_enable_proactive_handles_missing_hpa():
    """Test enable_proactive handles 404 errors gracefully"""
    print("\n=== Testing enable_proactive with missing HPA ===")
    
    from run_experiments import enable_proactive, MONITORED_SERVICES, NAMESPACE
    
    with patch('run_experiments.client.AutoscalingV2Api') as mock_autoscaling_class, \
         patch('run_experiments.apps_v1') as mock_apps_v1, \
         patch('run_experiments.time.sleep'):
        
        mock_autoscaling = Mock()
        mock_autoscaling_class.return_value = mock_autoscaling
        
        # Simulate 404 error (HPA not found)
        error_404 = client.exceptions.ApiException(status=404)
        mock_autoscaling.delete_namespaced_horizontal_pod_autoscaler.side_effect = error_404
        
        # Should not raise exception
        enable_proactive()
        
        print("✓ enable_proactive handles missing HPAs gracefully")


def test_enable_reactive():
    """Test enable_reactive scales controller to 0 and applies HPAs"""
    print("\n=== Testing enable_reactive ===")
    
    from run_experiments import enable_reactive, NAMESPACE
    
    # Create a mock path that exists
    mock_hpa_path = Mock()
    mock_hpa_path.exists.return_value = True
    mock_hpa_path.__str__.return_value = "/path/to/hpa-baseline.yaml"
    
    # Create mock for Path(__file__).parent.parent / "k8s" / "hpa-baseline.yaml"
    mock_file_path = Mock()
    mock_parent1 = Mock()
    mock_parent2 = Mock()
    mock_k8s_path = Mock()
    
    mock_file_path.parent = mock_parent1
    mock_parent1.parent = mock_parent2
    mock_parent2.__truediv__ = Mock(return_value=mock_k8s_path)
    mock_k8s_path.__truediv__ = Mock(return_value=mock_hpa_path)
    
    with patch('run_experiments.apps_v1') as mock_apps_v1, \
         patch('run_experiments.subprocess.run') as mock_subprocess, \
         patch('run_experiments.Path') as mock_path_class, \
         patch('run_experiments.time.sleep'), \
         patch('run_experiments.__file__', '/fake/path/run_experiments.py'):
        
        # Setup Path mock
        mock_path_class.return_value = mock_file_path
        
        # Mock successful kubectl apply
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Execute
        enable_reactive()
        
        # Verify scaling controller was scaled to 0 replicas
        mock_apps_v1.patch_namespaced_deployment_scale.assert_called_once_with(
            name="scaling-controller",
            namespace=NAMESPACE,
            body={"spec": {"replicas": 0}}
        )
        
        # Verify kubectl apply was called
        assert mock_subprocess.called
        
        print("✓ enable_reactive correctly scales controller to 0 and applies HPAs")


def test_condition_switching_integration():
    """Test switching between conditions"""
    print("\n=== Testing condition switching integration ===")
    
    from run_experiments import enable_proactive, enable_reactive, reset_cluster
    
    with patch('run_experiments.client.AutoscalingV2Api') as mock_autoscaling_class, \
         patch('run_experiments.apps_v1') as mock_apps_v1, \
         patch('run_experiments.subprocess.run') as mock_subprocess, \
         patch('run_experiments.Path') as mock_path_class, \
         patch('run_experiments.time.sleep'):
        
        mock_autoscaling = Mock()
        mock_autoscaling_class.return_value = mock_autoscaling
        
        # Mock HPA path
        mock_hpa_path = Mock()
        mock_hpa_path.exists.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Simulate switching: proactive -> reset -> reactive -> reset -> proactive
        print("  Switching to proactive...")
        enable_proactive()
        
        print("  Resetting cluster...")
        reset_cluster()
        
        print("  Switching to reactive...")
        enable_reactive()
        
        print("  Resetting cluster...")
        reset_cluster()
        
        print("  Switching back to proactive...")
        enable_proactive()
        
        print("✓ Condition switching integration test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Task 8.2: Condition Switching Tests")
    print("=" * 60)
    
    try:
        test_reset_cluster()
        test_enable_proactive()
        test_enable_proactive_handles_missing_hpa()
        test_enable_reactive()
        test_condition_switching_integration()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
