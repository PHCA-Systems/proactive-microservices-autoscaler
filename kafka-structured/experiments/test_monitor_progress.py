#!/usr/bin/env python3
"""
Test script for monitor_progress() function.
Creates a mock log file and tests the parsing logic.
"""

import os
import time
from pathlib import Path
from pipeline_orchestrator import monitor_progress, display_progress_dashboard


def create_mock_log_file(log_path: str, stage: int = 1):
    """
    Create a mock log file with sample content at different stages.
    
    Args:
        log_path: Path to create the log file
        stage: Which stage of the experiment to simulate (1-3)
    """
    content = []
    
    # Stage 1: Initial validation and setup
    if stage >= 1:
        content.extend([
            "="*70,
            "  EXPERIMENT SUITE STARTED: 2024-01-15 10:00:00",
            "="*70,
            "",
            "[VALIDATION] Checking infrastructure...",
            "  OK front-end",
            "  OK carts",
            "  OK orders",
            "",
            "[VALIDATION] ALL CHECKS PASSED",
            "",
            "="*70,
            "  SCHEDULE: 34 runs",
            "  Estimated duration: 5.7 hours",
            "  Estimated completion: 2024-01-15 15:42:00",
            "="*70,
            "",
        ])
    
    # Stage 2: First run in progress
    if stage >= 2:
        content.extend([
            "*"*70,
            "*  PROGRESS: 1/34 | Elapsed: 0min | ETA: 15:42:00",
            "*"*70,
            "",
            "#"*70,
            "#  RUN 1/34: proactive_constant_run01",
            "#  Started: 2024-01-15 10:00:00",
            "#  Condition: PROACTIVE | Pattern: constant | Rep: 1",
            "#"*70,
            "  [SETUP] Switching to PROACTIVE mode...",
            "    Deleted HPA: front-end-hpa",
            "    Deleted HPA: carts-hpa",
            "    Scaled scaling-controller to 1 replica in pipeline-cluster",
            "  Proactive system active.",
            "  [SETUP] Resetting cluster to 1 replica each...",
            "  Resetting all deployments to 1 replica...",
            "    Reset front-end to 1 replica",
            "    Reset carts to 1 replica",
            "  [LOAD] Locust started: constant pattern, 10min, 20 intervals",
            "  [DATA] Collecting 20 snapshots at 30s intervals...",
            "",
            "   idx |  time | FE rep   FE p95 | cart rep  cart p95 | ord rep  ord p95 | viols",
            "  --------------------------------------------------------------------------------",
            "     1 |  0.5m |     1r   45.2ms!|       1r    38.5ms!|      1r   42.1ms!| 3/7",
            "     2 |  1.0m |     2r   38.4ms!|       2r    35.2ms |      2r   36.8ms!| 2/7",
            "     3 |  1.5m |     2r   34.1ms |       2r    33.8ms |      2r   34.5ms | 0",
        ])
    
    # Stage 3: Multiple runs completed
    if stage >= 3:
        content.extend([
            "     4 |  2.0m |     2r   33.5ms |       2r    32.9ms |      2r   33.2ms | 0",
            "",
            "  [LOAD] Stopped after 600s. Settling 2 minutes...",
            "  [DONE] proactive_constant_run01 completed in 12.5 min",
            "  [DONE] Violation rate: 8.6% (12/140)",
            "  [DONE] Saved: results/proactive_constant_run01.jsonl",
            "",
            "  >>> COMPLETED 1/34: proactive_constant_run01 <<<",
            "",
            "*"*70,
            "*  PROGRESS: 2/34 | Elapsed: 13min | ETA: 15:35:00",
            "*"*70,
            "",
            "#"*70,
            "#  RUN 2/34: reactive_constant_run01",
            "#  Started: 2024-01-15 10:13:00",
            "#  Condition: REACTIVE | Pattern: constant | Rep: 1",
            "#"*70,
            "  [SETUP] Switching to REACTIVE mode...",
            "    Scaled scaling-controller to 0 replicas in pipeline-cluster",
            "    Applied HPA baseline from k8s/hpa-baseline.yaml",
            "  Reactive HPA baseline active.",
            "  [LOAD] Locust started: constant pattern, 10min, 20 intervals",
            "  [DATA] Collecting 20 snapshots at 30s intervals...",
            "",
            "   idx |  time | FE rep   FE p95 | cart rep  cart p95 | ord rep  ord p95 | viols",
            "  --------------------------------------------------------------------------------",
            "     1 |  0.5m |     1r   48.3ms!|       1r    41.2ms!|      1r   44.5ms!| 4/7",
            "     2 |  1.0m |     3r   36.7ms!|       3r    34.1ms |      3r   35.9ms!| 2/7",
        ])
    
    # Write to file
    with open(log_path, 'w') as f:
        f.write('\n'.join(content))


def test_monitor_progress():
    """Test the monitor_progress function with mock data."""
    print("Testing monitor_progress() function")
    print("="*70)
    
    # Create temporary log file
    test_log_path = "test_experiment_log.txt"
    
    try:
        # Test 1: Non-existent log file
        print("\nTest 1: Non-existent log file")
        print("-" * 70)
        if os.path.exists(test_log_path):
            os.remove(test_log_path)
        
        result = monitor_progress(test_log_path)
        print(f"Result: {result}")
        assert result is None, "Should return None for non-existent file"
        print("✓ PASSED: Returns None for non-existent file")
        
        # Test 2: Empty log file
        print("\nTest 2: Empty log file")
        print("-" * 70)
        Path(test_log_path).touch()
        result = monitor_progress(test_log_path)
        print(f"Result: {result}")
        assert result is None, "Should return None for empty file"
        print("✓ PASSED: Returns None for empty file")
        
        # Test 3: Log file with initial content (stage 1)
        print("\nTest 3: Initial validation stage")
        print("-" * 70)
        create_mock_log_file(test_log_path, stage=1)
        result = monitor_progress(test_log_path)
        print(f"Result: {result}")
        assert result is not None, "Should return progress info"
        print("✓ PASSED: Returns progress info for stage 1")
        display_progress_dashboard(result)
        
        # Test 4: Log file with first run in progress (stage 2)
        print("\nTest 4: First run in progress")
        print("-" * 70)
        create_mock_log_file(test_log_path, stage=2)
        result = monitor_progress(test_log_path)
        print(f"Result: {result}")
        assert result is not None, "Should return progress info"
        assert result['total_runs'] == 34, f"Expected 34 total runs, got {result['total_runs']}"
        assert result['current_condition'] == 'proactive', f"Expected proactive, got {result['current_condition']}"
        assert result['current_pattern'] == 'constant', f"Expected constant, got {result['current_pattern']}"
        print("✓ PASSED: Correctly parses first run information")
        display_progress_dashboard(result)
        
        # Test 5: Log file with multiple runs completed (stage 3)
        print("\nTest 5: Multiple runs completed")
        print("-" * 70)
        create_mock_log_file(test_log_path, stage=3)
        result = monitor_progress(test_log_path)
        print(f"Result: {result}")
        assert result is not None, "Should return progress info"
        assert result['total_runs'] == 34, f"Expected 34 total runs, got {result['total_runs']}"
        assert result['completed_runs'] >= 1, f"Expected at least 1 completed run, got {result['completed_runs']}"
        assert result['current_condition'] == 'reactive', f"Expected reactive, got {result['current_condition']}"
        assert result['elapsed_minutes'] == 13, f"Expected 13 elapsed minutes, got {result['elapsed_minutes']}"
        print("✓ PASSED: Correctly parses multiple runs")
        display_progress_dashboard(result)
        
        # Test 6: Display dashboard with None
        print("\nTest 6: Display dashboard with no data")
        print("-" * 70)
        display_progress_dashboard(None)
        print("✓ PASSED: Dashboard handles None gracefully")
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓")
        print("="*70)
        
    finally:
        # Cleanup
        if os.path.exists(test_log_path):
            os.remove(test_log_path)
            print(f"\nCleaned up test file: {test_log_path}")


if __name__ == "__main__":
    test_monitor_progress()
