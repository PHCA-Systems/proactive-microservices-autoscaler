#!/usr/bin/env python3
"""
Example usage of monitor_progress() function.
Demonstrates how to poll the log file periodically without blocking.
"""

import time
import sys
from pipeline_orchestrator import monitor_progress, display_progress_dashboard


def monitor_experiment_progress(
    log_file_path: str = "kafka-structured/experiments/experiment_run_log.txt",
    poll_interval_seconds: int = 30,
    max_iterations: int = None
):
    """
    Monitor experiment progress by polling the log file periodically.
    
    This function demonstrates the non-blocking polling pattern for monitoring
    long-running experiments. It polls every 30 seconds and displays a progress
    dashboard.
    
    Args:
        log_file_path: Path to the experiment log file
        poll_interval_seconds: How often to poll the log file (default: 30s)
        max_iterations: Maximum number of polling iterations (None = infinite)
    """
    print("Starting experiment progress monitor...")
    print(f"Log file: {log_file_path}")
    print(f"Poll interval: {poll_interval_seconds} seconds")
    print(f"Press Ctrl+C to stop monitoring\n")
    
    iteration = 0
    last_completed = 0
    
    try:
        while True:
            iteration += 1
            
            # Poll the log file
            progress_info = monitor_progress(log_file_path, poll_interval_seconds)
            
            # Display the dashboard
            display_progress_dashboard(progress_info)
            
            # Check if experiment is complete
            if progress_info is not None:
                completed = progress_info['completed_runs']
                total = progress_info['total_runs']
                
                # Detect when a new run completes
                if completed > last_completed:
                    print(f"\n🎉 Run {completed}/{total} completed!")
                    last_completed = completed
                
                # Check if all runs are complete
                if total > 0 and completed >= total:
                    print("\n" + "="*70)
                    print("  🎊 ALL EXPERIMENTS COMPLETED! 🎊")
                    print("="*70)
                    break
            
            # Check max iterations
            if max_iterations is not None and iteration >= max_iterations:
                print(f"\nReached maximum iterations ({max_iterations}). Stopping monitor.")
                break
            
            # Wait before next poll
            print(f"\nNext update in {poll_interval_seconds} seconds...")
            time.sleep(poll_interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user (Ctrl+C)")
        print("Experiment continues running in background.")
        sys.exit(0)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor experiment progress by polling log file"
    )
    parser.add_argument(
        "--log-file",
        default="kafka-structured/experiments/experiment_run_log.txt",
        help="Path to experiment log file"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of polling iterations (default: infinite)"
    )
    
    args = parser.parse_args()
    
    monitor_experiment_progress(
        log_file_path=args.log_file,
        poll_interval_seconds=args.interval,
        max_iterations=args.max_iterations
    )
