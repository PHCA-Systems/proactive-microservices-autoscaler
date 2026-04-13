#!/usr/bin/env python3
"""
Unit tests for pipeline orchestrator module.
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from pipeline_orchestrator import (
    InfraConfig,
    ExperimentConfig,
    ValidationResult,
    ValidationStatus,
    ExperimentRun,
    AnalysisResult,
    PipelineState,
    load_configuration,
    launch_experiment_suite,
)


def test_infra_config_defaults():
    """Test InfraConfig has correct default values."""
    config = InfraConfig()
    
    assert config.target_cluster == "gke_grad-phca_us-central1-a_sock-shop-cluster"
    assert config.pipeline_cluster == "gke_grad-phca_us-central1-a_pipeline-cluster"
    assert config.prometheus_url == "http://34.170.213.190:9090"
    assert config.locust_vm_ip == "35.222.116.125"
    assert config.locust_ssh_user == "User"
    assert config.sock_shop_ip == "104.154.246.88"
    assert config.slo_latency_ms == 35.68


def test_infra_config_from_environment():
    """Test InfraConfig loads from environment variables."""
    # Set environment variables
    os.environ["PROMETHEUS_URL"] = "http://test-prometheus:9090"
    os.environ["LOCUST_VM_IP"] = "192.168.1.100"
    
    config = InfraConfig.from_environment()
    
    assert config.prometheus_url == "http://test-prometheus:9090"
    assert config.locust_vm_ip == "192.168.1.100"
    
    # Clean up
    del os.environ["PROMETHEUS_URL"]
    del os.environ["LOCUST_VM_IP"]


def test_experiment_config_defaults():
    """Test ExperimentConfig has correct default values."""
    config = ExperimentConfig()
    
    assert config.total_runs == 34
    assert config.load_patterns == ["constant", "sine", "spike", "step"]
    assert config.conditions == ["proactive", "reactive"]
    assert config.repetitions_per_pattern == 4
    assert config.run_duration_minutes == 6
    assert config.interval_seconds == 30
    assert config.results_dir == "kafka-structured/experiments/results"


def test_experiment_config_creates_results_dir():
    """Test ExperimentConfig creates results directory."""
    test_dir = "kafka-structured/experiments/test_results"
    config = ExperimentConfig(results_dir=test_dir)
    
    assert Path(test_dir).exists()
    
    # Clean up
    Path(test_dir).rmdir()


def test_validation_result_success():
    """Test ValidationResult success creation."""
    result = ValidationResult.success()
    
    assert result.status == ValidationStatus.SUCCESS
    assert result.is_success is True
    assert result.error_message is None


def test_validation_result_failure():
    """Test ValidationResult failure creation."""
    error_msg = "Test error message"
    result = ValidationResult.failure(error_msg)
    
    assert result.status == ValidationStatus.FAILURE
    assert result.is_success is False
    assert result.error_message == error_msg


def test_experiment_run_structure():
    """Test ExperimentRun data structure."""
    run = ExperimentRun(
        run_id=1,
        condition="proactive",
        pattern="constant",
        start_time="2024-01-01T00:00:00",
        end_time="2024-01-01T00:10:00",
        slo_violations=5,
        avg_latency_ms=32.5,
        resource_usage=0.75,
        success=True,
        error_msg=None
    )
    
    assert run.run_id == 1
    assert run.condition == "proactive"
    assert run.pattern == "constant"
    assert run.success is True


def test_analysis_result_structure():
    """Test AnalysisResult data structure."""
    result = AnalysisResult(
        per_pattern_tables=["table1", "table2"],
        global_summary="Test summary",
        statistical_tests="Test stats",
        per_service_winners="Test winners"
    )
    
    assert len(result.per_pattern_tables) == 2
    assert result.global_summary == "Test summary"


def test_pipeline_state_structure():
    """Test PipelineState data structure."""
    state = PipelineState(
        phase="validation",
        completed_runs=0,
        failed_runs=[],
    )
    
    assert state.phase == "validation"
    assert state.completed_runs == 0
    assert len(state.failed_runs) == 0
    assert state.start_time != ""  # Should be auto-initialized


def test_pipeline_state_with_failures():
    """Test PipelineState tracks failed runs."""
    state = PipelineState(
        phase="execution",
        completed_runs=10,
        failed_runs=[3, 7, 9],
    )
    
    assert state.completed_runs == 10
    assert len(state.failed_runs) == 3
    assert 7 in state.failed_runs


def test_load_configuration():
    """Test configuration loading function."""
    infra_config, experiment_config = load_configuration()
    
    # Verify infra config
    assert isinstance(infra_config, InfraConfig)
    assert infra_config.prometheus_url == "http://34.170.213.190:9090"
    
    # Verify experiment config
    assert isinstance(experiment_config, ExperimentConfig)
    assert experiment_config.total_runs == 34


def test_launch_experiment_suite_creates_log_file():
    """Test launch_experiment_suite creates log file in correct location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary experiment config
        results_dir = os.path.join(tmpdir, "results")
        config = ExperimentConfig(results_dir=results_dir)
        
        # Mock the run_experiments.py script existence
        script_path = Path(__file__).parent / "run_experiments.py"
        
        with patch('subprocess.Popen') as mock_popen, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Mock process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Call the function
            if script_path.exists():
                process = launch_experiment_suite(config)
                
                # Verify process was created
                assert process is not None
                assert mock_popen.called
                
                # Verify command uses python -u
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "python" in cmd[0]
                assert "-u" in cmd
                assert "run_experiments.py" in str(cmd[-1])


def test_launch_experiment_suite_custom_log_path():
    """Test launch_experiment_suite accepts custom log file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results_dir = os.path.join(tmpdir, "results")
        config = ExperimentConfig(results_dir=results_dir)
        custom_log = os.path.join(tmpdir, "custom_log.txt")
        
        script_path = Path(__file__).parent / "run_experiments.py"
        
        with patch('subprocess.Popen') as mock_popen, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            if script_path.exists():
                process = launch_experiment_suite(config, log_file_path=custom_log)
                
                # Verify custom log path was used
                assert mock_file.called
                # Check that open was called with the custom log path
                mock_file.assert_called_with(custom_log, "w", buffering=1)


def test_launch_experiment_suite_missing_script():
    """Test launch_experiment_suite raises error if run_experiments.py missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results_dir = os.path.join(tmpdir, "results")
        config = ExperimentConfig(results_dir=results_dir)
        
        # Mock Path.exists to return False
        with patch('pathlib.Path.exists', return_value=False):
            try:
                launch_experiment_suite(config)
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError as e:
                assert "run_experiments.py not found" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
