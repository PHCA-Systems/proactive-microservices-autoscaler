#!/usr/bin/env python3
"""
Pipeline Orchestrator Module
Automated orchestration system for executing 34-run experiment suite
comparing proactive vs reactive autoscaling across 4 load patterns.
"""

import os
import subprocess
import time
import json
import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
from enum import Enum


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class InfraConfig:
    """Infrastructure configuration with endpoints and credentials."""
    target_cluster: str = "gke_grad-phca_us-central1-a_sock-shop-cluster"
    pipeline_cluster: str = "gke_grad-phca_us-central1-a_pipeline-cluster"
    prometheus_url: str = "http://34.170.213.190:9090"
    locust_vm_ip: str = "35.222.116.125"
    locust_ssh_user: str = "User"
    locust_ssh_key: str = os.path.expanduser("~/.ssh/google_compute_engine")
    sock_shop_ip: str = "104.154.246.88"
    slo_latency_ms: float = 35.68
    
    @classmethod
    def from_environment(cls) -> 'InfraConfig':
        """Load configuration from environment variables with defaults."""
        return cls(
            prometheus_url=os.getenv("PROMETHEUS_URL", cls.prometheus_url),
            locust_vm_ip=os.getenv("LOCUST_VM_IP", cls.locust_vm_ip),
            locust_ssh_user=os.getenv("LOCUST_SSH_USER", cls.locust_ssh_user),
            locust_ssh_key=os.getenv("LOCUST_SSH_KEY", cls.locust_ssh_key),
            sock_shop_ip=os.getenv("SOCK_SHOP_EXTERNAL_IP", cls.sock_shop_ip),
        )


@dataclass
class ExperimentConfig:
    """Experiment suite configuration."""
    total_runs: int = 34
    load_patterns: List[str] = field(default_factory=lambda: ["constant", "sine", "spike", "step"])
    conditions: List[str] = field(default_factory=lambda: ["proactive", "reactive"])
    repetitions_per_pattern: int = 4
    run_duration_minutes: int = 6
    interval_seconds: int = 30
    results_dir: str = "kafka-structured/experiments/results"
    
    def __post_init__(self):
        """Ensure results directory exists."""
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)


class ValidationStatus(Enum):
    """Validation result status."""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class ValidationResult:
    """Result of infrastructure validation."""
    status: ValidationStatus
    error_message: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if validation succeeded."""
        return self.status == ValidationStatus.SUCCESS
    
    @classmethod
    def success(cls) -> 'ValidationResult':
        """Create a success result."""
        return cls(status=ValidationStatus.SUCCESS)
    
    @classmethod
    def failure(cls, message: str) -> 'ValidationResult':
        """Create a failure result with error message."""
        return cls(status=ValidationStatus.FAILURE, error_message=message)


@dataclass
class ExperimentRun:
    """Result of a single experiment run."""
    run_id: int
    condition: str
    pattern: str
    start_time: str
    end_time: str
    slo_violations: int
    avg_latency_ms: float
    resource_usage: float
    success: bool
    error_msg: Optional[str] = None


@dataclass
class AnalysisResult:
    """Statistical analysis results."""
    per_pattern_tables: List[str] = field(default_factory=list)
    global_summary: str = ""
    statistical_tests: str = ""
    per_service_winners: str = ""


@dataclass
class PipelineState:
    """Current state of pipeline execution."""
    phase: str
    completed_runs: int
    failed_runs: List[int] = field(default_factory=list)
    start_time: str = ""
    estimated_completion: str = ""
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if not self.start_time:
            self.start_time = datetime.now().isoformat()


# ============================================================================
# Configuration Loading
# ============================================================================

def load_configuration() -> Tuple[InfraConfig, ExperimentConfig]:
    """
    Load infrastructure and experiment configuration.
    
    Returns:
        Tuple of (InfraConfig, ExperimentConfig) with values loaded from
        environment variables and constants.
    """
    infra_config = InfraConfig.from_environment()
    experiment_config = ExperimentConfig()
    
    return infra_config, experiment_config


# ============================================================================
# Infrastructure Validation
# ============================================================================

def validate_infrastructure(config: InfraConfig) -> ValidationResult:
    """
    Validate that all infrastructure components are reachable.
    
    Preconditions:
        - config contains valid non-empty strings for all endpoints
        - Network connectivity is available
        - SSH key file exists at specified path
    
    Postconditions:
        - Returns ValidationResult.success() if all components are reachable
        - Returns ValidationResult.failure(msg) with descriptive error if any component fails
        - No side effects on infrastructure state
    
    Args:
        config: Infrastructure configuration
        
    Returns:
        ValidationResult indicating success or failure with error message
    """
    print("[VALIDATION] Checking infrastructure components...")
    
    # Check Prometheus availability
    print(f"  Checking Prometheus at {config.prometheus_url}...")
    try:
        response = requests.get(
            f"{config.prometheus_url}/api/v1/query",
            params={"query": "up"},
            timeout=10
        )
        if response.status_code != 200:
            return ValidationResult.failure(
                f"Prometheus unreachable: HTTP {response.status_code}"
            )
        print("    ✓ Prometheus OK")
    except Exception as e:
        return ValidationResult.failure(f"Prometheus unreachable: {e}")
    
    # Check Locust VM SSH connectivity
    print(f"  Checking Locust VM SSH at {config.locust_vm_ip}...")
    try:
        result = subprocess.run(
            [
                "ssh",
                "-i", config.locust_ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=15",
                f"{config.locust_ssh_user}@{config.locust_vm_ip}",
                "echo OK"
            ],
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode != 0:
            return ValidationResult.failure(
                f"Locust VM SSH failed: {result.stderr[:200]}"
            )
        print("    ✓ Locust VM SSH OK")
    except Exception as e:
        return ValidationResult.failure(f"Locust VM SSH failed: {e}")
    
    # Check Kubernetes cluster connectivity
    print(f"  Checking Kubernetes cluster {config.target_cluster}...")
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info", "--context", config.target_cluster],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            return ValidationResult.failure(
                f"Kubernetes cluster unreachable: {result.stderr[:200]}"
            )
        print("    ✓ Kubernetes cluster OK")
    except Exception as e:
        return ValidationResult.failure(f"Kubernetes cluster unreachable: {e}")
    
    # Check Sock Shop endpoint
    print(f"  Checking Sock Shop at http://{config.sock_shop_ip}...")
    try:
        response = requests.get(
            f"http://{config.sock_shop_ip}",
            timeout=10
        )
        if response.status_code not in [200, 301, 302]:
            return ValidationResult.failure(
                f"Sock Shop unreachable: HTTP {response.status_code}"
            )
        print("    ✓ Sock Shop endpoint OK")
    except Exception as e:
        return ValidationResult.failure(f"Sock Shop unreachable: {e}")
    
    print("[VALIDATION] All infrastructure checks passed ✓")
    return ValidationResult.success()


# ============================================================================
# Experiment Suite Execution
# ============================================================================

def launch_experiment_suite(
    experiment_config: ExperimentConfig,
    log_file_path: Optional[str] = None
) -> subprocess.Popen:
    """
    Launch the experiment suite by invoking run_experiments.py.
    
    This function starts the experiment runner as a background process with
    unbuffered output redirected to a log file for real-time monitoring.
    
    Preconditions:
        - Infrastructure validation has passed
        - run_experiments.py exists in kafka-structured/experiments/
        - Results directory exists and is writable
        - Python interpreter is available
    
    Postconditions:
        - Returns subprocess.Popen handle for the running experiment process
        - Process runs with unbuffered output (-u flag)
        - stdout/stderr are redirected to log file
        - NO --pause-before-start flag is passed
        - Process runs in background and can be monitored
    
    Args:
        experiment_config: Experiment configuration (used for log file path)
        log_file_path: Optional path to log file. If None, uses default location
                      in experiments directory.
    
    Returns:
        subprocess.Popen handle for monitoring the experiment process
    """
    # Determine log file path
    if log_file_path is None:
        log_file_path = os.path.join(
            os.path.dirname(experiment_config.results_dir),
            "experiment_run_log.txt"
        )
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Path to run_experiments.py
    script_dir = Path(__file__).parent
    run_experiments_script = script_dir / "run_experiments.py"
    
    if not run_experiments_script.exists():
        raise FileNotFoundError(
            f"run_experiments.py not found at {run_experiments_script}"
        )
    
    print(f"[LAUNCHER] Starting experiment suite...")
    print(f"  Script: {run_experiments_script}")
    print(f"  Log file: {log_file_path}")
    print(f"  Results directory: {experiment_config.results_dir}")
    
    # Open log file for writing
    log_file = open(log_file_path, "w", buffering=1)  # Line buffered
    
    # Build command - use python -u for unbuffered output
    # NO --pause-before-start flag as per requirements
    cmd = [
        "python",
        "-u",  # Unbuffered output for real-time log monitoring
        str(run_experiments_script)
    ]
    
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Starting process in background...")
    
    # Start the process with output redirected to log file
    process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
        bufsize=1,  # Line buffered
        cwd=str(script_dir)  # Run in experiments directory
    )
    
    print(f"  Process started with PID: {process.pid}")
    print(f"  Monitor progress by tailing: {log_file_path}")
    print(f"  Process handle returned for monitoring")
    
    return process


# ============================================================================
# Progress Monitoring
# ============================================================================

def monitor_progress(
    log_file_path: str,
    poll_interval_seconds: int = 30
) -> Optional[dict]:
    """
    Monitor experiment progress by parsing the log file.
    
    This function tails the log file to extract current progress information
    including completed runs, current run details, and estimated completion time.
    Designed to be called periodically without blocking.
    
    Preconditions:
        - log_file_path points to a valid file path (may not exist yet)
        - poll_interval_seconds > 0
    
    Postconditions:
        - Returns dict with progress information if log file exists and has content
        - Returns None if log file doesn't exist or is empty
        - No modifications to log file or file system
        - Function completes quickly (non-blocking)
    
    Args:
        log_file_path: Path to the experiment log file to monitor
        poll_interval_seconds: Polling interval (for display purposes only)
    
    Returns:
        Dictionary with progress information:
        {
            'completed_runs': int,
            'total_runs': int,
            'current_run': str,
            'current_condition': str,
            'current_pattern': str,
            'elapsed_minutes': float,
            'eta': str,
            'last_lines': List[str]
        }
        Returns None if log file doesn't exist or cannot be read.
    """
    # Check if log file exists
    log_path = Path(log_file_path)
    if not log_path.exists():
        return None
    
    try:
        # Read last 50 lines of log file for parsing
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Seek to end and read backwards to get last N lines efficiently
            # For simplicity, read entire file if small, or tail if large
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()
            
            if file_size == 0:
                return None
            
            # Read last ~10KB or entire file if smaller
            read_size = min(10240, file_size)
            f.seek(max(0, file_size - read_size))
            content = f.read()
            lines = content.splitlines()
            
            # Keep last 50 lines for analysis
            last_lines = lines[-50:] if len(lines) > 50 else lines
    
    except Exception as e:
        print(f"Warning: Could not read log file: {e}")
        return None
    
    # Parse progress information from log lines
    progress_info = {
        'completed_runs': 0,
        'total_runs': 0,
        'current_run': 'Unknown',
        'current_condition': 'Unknown',
        'current_pattern': 'Unknown',
        'elapsed_minutes': 0.0,
        'eta': 'Unknown',
        'last_lines': last_lines[-20:]  # Keep last 20 lines for display
    }
    
    # Parse lines in reverse order to get most recent information
    for line in reversed(last_lines):
        # Look for PROGRESS markers: "PROGRESS: {idx}/{total} | Elapsed: {elapsed}min | ETA: {eta}"
        if 'PROGRESS:' in line and '|' in line:
            try:
                # Extract progress: "PROGRESS: 5/34 | Elapsed: 50min | ETA: 12:34:56"
                parts = line.split('|')
                if len(parts) >= 3:
                    # Parse "PROGRESS: 5/34"
                    progress_part = parts[0].strip()
                    if 'PROGRESS:' in progress_part:
                        run_info = progress_part.split('PROGRESS:')[1].strip()
                        if '/' in run_info:
                            completed, total = run_info.split('/')
                            progress_info['completed_runs'] = int(completed.strip()) - 1  # Current run not completed yet
                            progress_info['total_runs'] = int(total.strip())
                    
                    # Parse "Elapsed: 50min"
                    elapsed_part = parts[1].strip()
                    if 'Elapsed:' in elapsed_part:
                        elapsed_str = elapsed_part.split('Elapsed:')[1].strip().replace('min', '')
                        progress_info['elapsed_minutes'] = float(elapsed_str)
                    
                    # Parse "ETA: 12:34:56"
                    eta_part = parts[2].strip()
                    if 'ETA:' in eta_part:
                        eta_str = eta_part.split('ETA:')[1].strip()
                        progress_info['eta'] = eta_str
                    
                    break  # Found most recent progress marker
            except (ValueError, IndexError) as e:
                continue  # Skip malformed lines
        
        # Look for RUN markers: "RUN 5/34: proactive_constant_run01"
        if 'RUN' in line and ':' in line and '/' in line:
            try:
                # Extract: "RUN 5/34: proactive_constant_run01"
                if '#  RUN' in line:
                    run_part = line.split('#  RUN')[1].strip()
                    if ':' in run_part:
                        run_num_part, run_label = run_part.split(':', 1)
                        run_label = run_label.strip()
                        
                        # Parse run label: "proactive_constant_run01"
                        if '_' in run_label:
                            parts = run_label.split('_')
                            if len(parts) >= 3:
                                progress_info['current_condition'] = parts[0]
                                progress_info['current_pattern'] = parts[1]
                                progress_info['current_run'] = run_label
                        
                        # Parse run numbers if not already found
                        if progress_info['total_runs'] == 0 and '/' in run_num_part:
                            current, total = run_num_part.split('/')
                            progress_info['completed_runs'] = int(current.strip()) - 1
                            progress_info['total_runs'] = int(total.strip())
            except (ValueError, IndexError):
                continue
    
    # Look for COMPLETED markers to get accurate completed count
    completed_count = 0
    for line in last_lines:
        if 'COMPLETED' in line and '/' in line:
            completed_count += 1
    
    # Use completed count if it's more accurate
    if completed_count > progress_info['completed_runs']:
        progress_info['completed_runs'] = completed_count
    
    return progress_info


def display_progress_dashboard(progress_info: Optional[dict]) -> None:
    """
    Display a clean progress dashboard to the console.
    
    Args:
        progress_info: Progress information dictionary from monitor_progress()
                      or None if no progress available
    """
    print("\n" + "="*70)
    print("  EXPERIMENT PROGRESS DASHBOARD")
    print("="*70)
    
    if progress_info is None:
        print("  Status: Waiting for experiment to start...")
        print("  Log file not yet available or empty")
        print("="*70)
        return
    
    # Display progress summary
    completed = progress_info['completed_runs']
    total = progress_info['total_runs']
    
    if total > 0:
        progress_pct = (completed / total) * 100
        progress_bar_width = 40
        filled = int(progress_bar_width * completed / total)
        bar = '█' * filled + '░' * (progress_bar_width - filled)
        
        print(f"  Progress: [{bar}] {progress_pct:.1f}%")
        print(f"  Completed: {completed}/{total} runs")
    else:
        print(f"  Progress: Initializing...")
        print(f"  Completed: {completed} runs")
    
    # Display current run information
    print(f"\n  Current Run:")
    print(f"    Run ID: {progress_info['current_run']}")
    print(f"    Condition: {progress_info['current_condition'].upper()}")
    print(f"    Pattern: {progress_info['current_pattern'].upper()}")
    
    # Display timing information
    print(f"\n  Timing:")
    print(f"    Elapsed: {progress_info['elapsed_minutes']:.0f} minutes")
    print(f"    ETA: {progress_info['eta']}")
    
    if total > 0 and completed > 0:
        avg_time_per_run = progress_info['elapsed_minutes'] / completed
        remaining_runs = total - completed
        estimated_remaining = avg_time_per_run * remaining_runs
        print(f"    Estimated Remaining: {estimated_remaining:.0f} minutes ({estimated_remaining/60:.1f} hours)")
    
    # Display last few log lines
    print(f"\n  Recent Activity (last 5 lines):")
    if progress_info['last_lines']:
        for line in progress_info['last_lines'][-5:]:
            # Truncate long lines
            display_line = line[:100] + '...' if len(line) > 100 else line
            print(f"    {display_line}")
    
    print("="*70)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for pipeline orchestrator."""
    print("="*70)
    print("  PIPELINE ORCHESTRATOR")
    print("  Graduation Experiment Suite - 34 Runs")
    print("="*70)
    
    # Load configuration
    infra_config, experiment_config = load_configuration()
    
    print(f"\nConfiguration loaded:")
    print(f"  Total runs: {experiment_config.total_runs}")
    print(f"  Patterns: {', '.join(experiment_config.load_patterns)}")
    print(f"  Conditions: {', '.join(experiment_config.conditions)}")
    print(f"  Results directory: {experiment_config.results_dir}")
    print(f"  Prometheus: {infra_config.prometheus_url}")
    print(f"  Locust VM: {infra_config.locust_vm_ip}")
    print(f"  Sock Shop: {infra_config.sock_shop_ip}")
    
    # Validate infrastructure
    print()
    validation_result = validate_infrastructure(infra_config)
    
    if not validation_result.is_success:
        print(f"\n❌ Infrastructure validation failed: {validation_result.error_message}")
        print("Please fix the issues above and try again.")
        return 1
    
    print("\n✓ Infrastructure validation passed")
    print("\nPipeline orchestrator initialized successfully.")
    print("Ready to execute experiment suite.")
    
    # Example: Launch experiment suite and monitor progress
    # Uncomment the following lines to actually run experiments:
    #
    # print("\nLaunching experiment suite...")
    # log_file = "kafka-structured/experiments/experiment_run_log.txt"
    # process = launch_experiment_suite(experiment_config, log_file)
    # 
    # print("\nMonitoring progress (polling every 30 seconds)...")
    # try:
    #     while process.poll() is None:  # While process is running
    #         time.sleep(30)  # Poll every 30 seconds
    #         progress_info = monitor_progress(log_file)
    #         display_progress_dashboard(progress_info)
    # except KeyboardInterrupt:
    #     print("\nMonitoring interrupted. Experiment continues in background.")
    # 
    # # Wait for process to complete
    # return_code = process.wait()
    # print(f"\nExperiment suite completed with return code: {return_code}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
