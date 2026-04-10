#!/usr/bin/env python3
"""
run_experiment.py
=================
Unified runner for a Sock Shop load-test experiment:
  1. Start Sock Shop + Prometheus/Grafana  (docker compose)
  2. Start Locust load generator           (background process)
  3. Start Prometheus metrics collector    (background process)
  4. Wait for everything to finish, then print a summary

Usage
-----
  # 10-min constant load (all defaults)
  python run_experiment.py

  # 30-min ramp load, custom CSV
  python run_experiment.py --pattern ramp --duration 30 --output ramp_metrics.csv

  # Stack already running, 15-min spike test
  python run_experiment.py --skip-docker --pattern spike --duration 15

  # Basic pattern with explicit user count
  python run_experiment.py --pattern basic --users 100 --spawn-rate 10 --duration 20
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)

def ok(msg: str) -> None:
    print(f"    [OK]  {msg}", flush=True)

def warn(msg: str) -> None:
    print(f"    [!!]  {msg}", flush=True)

def die(msg: str) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Mixed Patterns Runner (4 hours)
# ---------------------------------------------------------------------------
def run_mixed_patterns(args, script_dir, project_root, compose_dir, load_dir, output_dir, logs_dir, csv_dir):
    """Run 4 hours of mixed load patterns with varying durations."""
    
    # Define the pattern sequence (total = 240 minutes = 4 hours)
    pattern_sequence = [
        ("ramp", 15),      # 15 min
        ("constant", 20),  # 20 min
        ("spike", 10),     # 10 min
        ("step", 30),      # 30 min
        ("ramp", 25),      # 25 min
        ("constant", 15),  # 15 min
        ("spike", 5),      # 5 min
        ("step", 20),      # 20 min
        ("ramp", 10),      # 10 min
        ("constant", 30),  # 30 min
        ("spike", 15),     # 15 min
        ("step", 10),      # 10 min
        ("ramp", 20),      # 20 min
        ("constant", 10),  # 10 min
        ("spike", 15),     # 15 min
    ]
    
    total_duration = sum(duration for _, duration in pattern_sequence)
    
    step(f"Starting 4-hour mixed pattern test ({total_duration} minutes total)")
    ok(f"Pattern sequence: {len(pattern_sequence)} segments")
    for i, (pattern, duration) in enumerate(pattern_sequence, 1):
        print(f"    {i:2d}. {pattern:8s} - {duration:2d} min")
    
    # Start docker if needed
    if not args.skip_docker:
        step("Starting Sock Shop + Prometheus/Grafana (docker compose)")
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", str(compose_dir / "docker-compose.yml"),
                "-f", str(compose_dir / "docker-compose.monitoring.yml"),
                "up", "-d",
                "--remove-orphans",
            ],
            cwd=str(compose_dir),
        )
        if result.returncode != 0:
            warn(f"docker compose exited with code {result.returncode}")
        else:
            ok("All containers started successfully.")
        ok("Waiting 20 s for services to initialise...")
        time.sleep(20)
    
    # Install dependencies
    step("Checking Python dependencies")
    py = sys.executable
    subprocess.run(
        [py, "-m", "pip", "install", "--quiet", "--upgrade",
         "locust>=2.15.0", "requests>=2.28.0"],
        check=True,
    )
    ok("locust and requests are ready")
    
    # Start metrics collector for the full 4 hours
    output_csv_path = csv_dir / "mixed_4hour_metrics.csv"
    collector_script = script_dir / "collect_metrics.py"
    collector_cmd = [
        py, str(collector_script),
        "--prometheus", args.prometheus,
        "--duration",   str(total_duration),
        "--output",     str(output_csv_path),
    ]
    
    step("Starting metrics collector for full 4-hour duration")
    coll_log_out = str(logs_dir / "collector_mixed_stdout.log")
    coll_log_err = str(logs_dir / "collector_mixed_stderr.log")
    with open(coll_log_out, "w") as cout, open(coll_log_err, "w") as cerr:
        coll_proc = subprocess.Popen(collector_cmd, stdout=cout, stderr=cerr)
    ok(f"Collector started  PID={coll_proc.pid}")
    
    time.sleep(2)
    
    # Run each pattern sequentially
    print()
    print("="*70)
    print("  STARTING 4-HOUR MIXED PATTERN TEST")
    print("="*70)
    print()
    
    pattern_users  = {"constant": 50, "step": 50, "spike": 10, "ramp": 10}
    pattern_spawn  = {"constant": 5,  "step": 5,  "spike": 2,  "ramp": 2}
    
    start_time = time.time()
    
    for segment_num, (pattern, duration_min) in enumerate(pattern_sequence, 1):
        elapsed_total = (time.time() - start_time) / 60
        remaining_total = total_duration - elapsed_total
        
        step(f"Segment {segment_num}/{len(pattern_sequence)}: {pattern} for {duration_min} minutes")
        ok(f"Total elapsed: {int(elapsed_total)}m, Remaining: {int(remaining_total)}m")
        
        # Build locust command
        locust_file = load_dir / "src" / f"locustfile_{pattern}.py"
        if not locust_file.exists():
            warn(f"locustfile_{pattern}.py not found — skipping")
            continue
        
        duration_sec = duration_min * 60
        locust_users = pattern_users[pattern]
        locust_spawn = pattern_spawn[pattern]
        
        locust_cmd = [
            py, "-m", "locust",
            "-f", str(locust_file),
            "--headless",
            "--host",        args.host,
            "--users",       str(locust_users),
            "--spawn-rate",  str(locust_spawn),
            "--run-time",    f"{duration_sec}s",
        ]
        
        locust_env = os.environ.copy()
        locust_env["LOCUST_RUN_TIME_MINUTES"] = str(duration_min)
        
        # Start locust for this segment
        locust_log_out = str(logs_dir / f"locust_mixed_seg{segment_num}_{pattern}_stdout.log")
        locust_log_err = str(logs_dir / f"locust_mixed_seg{segment_num}_{pattern}_stderr.log")
        
        with open(locust_log_out, "w") as lout, open(locust_log_err, "w") as lerr:
            locust_proc = subprocess.Popen(locust_cmd, stdout=lout, stderr=lerr, env=locust_env)
        
        ok(f"Locust started  PID={locust_proc.pid}  pattern={pattern}  duration={duration_min}m")
        
        # Wait for this segment to complete
        segment_start = time.time()
        try:
            while locust_proc.poll() is None:
                elapsed_segment = time.time() - segment_start
                remaining_segment = duration_sec - elapsed_segment
                
                if int(elapsed_segment) % 30 == 0 and elapsed_segment > 0:  # Update every 30s
                    progress = min(100, (elapsed_segment / duration_sec) * 100)
                    print(f"    [{int(progress):3d}%] Segment {segment_num}: {int(elapsed_segment/60)}m {int(elapsed_segment%60):02d}s / {duration_min}m", flush=True)
                
                time.sleep(1)
            
            # Wait a bit for process to fully exit
            locust_proc.wait(timeout=5)
            ok(f"Segment {segment_num} completed (exit code {locust_proc.returncode})")
            
        except KeyboardInterrupt:
            warn("Interrupted — stopping current segment...")
            locust_proc.terminate()
            locust_proc.wait(timeout=5)
            warn("Stopping collector...")
            coll_proc.terminate()
            coll_proc.wait(timeout=5)
            die("Experiment aborted by user")
        
        # Small gap between segments
        if segment_num < len(pattern_sequence):
            print("    Waiting 5s before next segment...", flush=True)
            time.sleep(5)
    
    # Wait for collector to finish
    step("Waiting for metrics collector to complete...")
    try:
        coll_proc.wait(timeout=30)
        ok(f"Collector finished (exit code {coll_proc.returncode})")
    except subprocess.TimeoutExpired:
        warn("Collector timeout — terminating")
        coll_proc.terminate()
        coll_proc.wait(timeout=5)
    
    # Summary
    total_elapsed = (time.time() - start_time) / 60
    step("4-hour mixed pattern test complete!")
    ok(f"Total duration: {int(total_elapsed)} minutes")
    ok(f"Metrics CSV: {output_csv_path}")
    ok(f"Logs: output/logs/locust_mixed_seg*")
    
    # Count rows
    actual_rows = 0
    try:
        if os.path.exists(str(output_csv_path)):
            with open(str(output_csv_path), "r") as f:
                actual_rows = sum(1 for line in f) - 1
    except Exception:
        pass
    
    expected_rows = total_duration * 2 * 7  # 2 polls/min × 7 services
    ok(f"Expected rows: {expected_rows}, Actual rows: {actual_rows}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.resolve()
    compose_dir  = project_root / "microservices-demo" / "deploy" / "docker-compose"
    load_dir     = project_root / "load-testing"
    output_dir   = project_root / "output"
    logs_dir     = output_dir / "logs"
    csv_dir      = output_dir / "csv"
    
    # Ensure output directories exist
    output_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    csv_dir.mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(
        description="Run a full Sock Shop load-test experiment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pattern",
        choices=["constant", "step", "spike", "ramp", "basic"],
        default="constant",
        help="Load pattern")
    parser.add_argument("--gen4patterns", action="store_true",
        help="Generate 4-hour mixed pattern test (ignores --pattern and --duration)")
    parser.add_argument("--users",       type=int, default=50,
        help="Concurrent users (basic pattern only)")
    parser.add_argument("--spawn-rate",  type=int, default=5,
        help="User spawn-rate per second (basic pattern only)")
    parser.add_argument("--duration",    type=int, default=10,
        help="Duration in MINUTES")
    parser.add_argument("--host",        default="http://localhost:80",
        help="Sock Shop front-end URL for Locust")
    parser.add_argument("--prometheus",  default="http://localhost:9090",
        help="Prometheus base URL for the metrics collector")
    parser.add_argument("--output",      default="sockshop_metrics.csv",
        help="Output CSV filename (will be saved in output/csv/)")
    parser.add_argument("--skip-docker", action="store_true",
        help="Skip docker-compose (use if the stack is already running)")
    args = parser.parse_args()

    # Handle --gen4patterns mode
    if args.gen4patterns:
        run_mixed_patterns(args, script_dir, project_root, compose_dir, load_dir, output_dir, logs_dir, csv_dir)
        return

    duration_sec = args.duration * 60
    
    # Construct full output path
    output_csv_path = csv_dir / args.output

    # ------------------------------------------------------------------
    # 0. Pre-flight
    # ------------------------------------------------------------------
    step("Pre-flight checks")

    py = sys.executable
    ok(f"Python: {sys.version.split()[0]}  ({py})")

    if not args.skip_docker:
        docker_ok = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True
        )
        if docker_ok.returncode != 0:
            die("docker not found. Install Docker Desktop or use --skip-docker.")
        ok(f"Docker: {docker_ok.stdout.strip()}")

    # ------------------------------------------------------------------
    # 1. Python dependencies
    # ------------------------------------------------------------------
    step("Checking Python dependencies")
    subprocess.run(
        [py, "-m", "pip", "install", "--quiet", "--upgrade",
         "locust>=2.15.0", "requests>=2.28.0"],
        check=True,
    )
    ok("locust and requests are ready")

    # ------------------------------------------------------------------
    # 2. Start Sock Shop stack
    # ------------------------------------------------------------------
    if not args.skip_docker:
        step("Starting Sock Shop + Prometheus/Grafana (docker compose)")
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", str(compose_dir / "docker-compose.yml"),
                "-f", str(compose_dir / "docker-compose.monitoring.yml"),
                "up", "-d",
                "--remove-orphans",
            ],
            cwd=str(compose_dir),
        )
        if result.returncode != 0:
            warn(f"docker compose exited with code {result.returncode} — some containers may have failed.")
            warn("Continuing anyway (most services may still be running).")
            warn("Check 'docker ps' to confirm the stack is healthy before interpreting results.")
        else:
            ok("All containers started successfully.")
        ok("Waiting 20 s for services to initialise...")
        time.sleep(20)
    else:
        warn("Skipping docker-compose (--skip-docker was set)")

    # ------------------------------------------------------------------
    # 3. Build Locust command
    # ------------------------------------------------------------------
    step(f"Configuring load generator  pattern={args.pattern}  duration={args.duration}m")

    pattern_users  = {"constant": 50, "step": 50, "spike": 10, "ramp": 10}
    pattern_spawn  = {"constant": 5,  "step": 5,  "spike": 2,  "ramp": 2}

    if args.pattern == "basic":
        locust_file = load_dir / "src" / "locustfile.py"
        locust_users = args.users
        locust_spawn = args.spawn_rate
    else:
        locust_file = load_dir / "src" / f"locustfile_{args.pattern}.py"
        if not locust_file.exists():
            warn(f"locustfile_{args.pattern}.py not found — falling back to locustfile.py")
            locust_file = load_dir / "src" / "locustfile.py"
        locust_users = pattern_users[args.pattern]
        locust_spawn = pattern_spawn[args.pattern]

    locust_cmd = [
        py, "-m", "locust",
        "-f", str(locust_file),
        "--headless",
        "--host",        args.host,
        "--users",       str(locust_users),
        "--spawn-rate",  str(locust_spawn),
        "--run-time",    f"{duration_sec}s",
    ]
    
    # Set environment variable for LoadShape classes to read duration
    locust_env = os.environ.copy()
    locust_env["LOCUST_RUN_TIME_MINUTES"] = str(args.duration)

    ok(f"Locust file : {locust_file}")
    ok(f"Target host : {args.host}")
    ok(f"Users       : {locust_users}  spawn-rate: {locust_spawn}")
    ok(f"Runtime     : {duration_sec}s")

    # ------------------------------------------------------------------
    # 4. Build collector command
    # ------------------------------------------------------------------
    step("Configuring metrics collector")

    collector_script = script_dir / "collect_metrics.py"
    collector_cmd = [
        py, str(collector_script),
        "--prometheus", args.prometheus,
        "--duration",   str(args.duration),
        "--output",     str(output_csv_path),
    ]

    ok(f"Prometheus  : {args.prometheus}")
    ok(f"Output CSV  : {output_csv_path}")

    # ------------------------------------------------------------------
    # 5. Launch both in background
    # ------------------------------------------------------------------
    locust_log_out = str(logs_dir / "locust_stdout.log")
    locust_log_err = str(logs_dir / "locust_stderr.log")
    coll_log_out   = str(logs_dir / "collector_stdout.log")
    coll_log_err   = str(logs_dir / "collector_stderr.log")

    step("Launching load generator...")
    with open(locust_log_out, "w") as lout, open(locust_log_err, "w") as lerr:
        locust_proc = subprocess.Popen(locust_cmd, stdout=lout, stderr=lerr, env=locust_env)
    ok(f"Locust started  PID={locust_proc.pid}  logs: output/logs/locust_stdout.log")

    warn("Giving Locust 5 s to connect before starting the collector...")
    time.sleep(5)

    step("Launching metrics collector...")
    with open(coll_log_out, "w") as cout, open(coll_log_err, "w") as cerr:
        coll_proc = subprocess.Popen(collector_cmd, stdout=cout, stderr=cerr)
    ok(f"Collector started  PID={coll_proc.pid}  logs: output/logs/collector_stdout.log")

    # ------------------------------------------------------------------
    # 6. Status banner
    # ------------------------------------------------------------------
    print()
    print("---------------------------------------------------")
    print("  Experiment is running")
    print(f"  Pattern  : {args.pattern}")
    print(f"  Duration : {args.duration} minute(s)")
    print(f"  CSV out  : {output_csv_path}")
    print("  Grafana  : http://localhost:3000  (admin / foobar)")
    print("  Press Ctrl+C to abort early")
    print("---------------------------------------------------")
    print()

    # ------------------------------------------------------------------
    # 7. Wait for completion with live status updates
    # ------------------------------------------------------------------
    try:
        start_time = time.time()
        update_interval = 10  # seconds
        last_update = start_time
        
        while locust_proc.poll() is None and coll_proc.poll() is None:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = duration_sec - elapsed
            
            if current_time - last_update >= update_interval:
                # Calculate progress
                progress_pct = min(100, (elapsed / duration_sec) * 100)
                remaining_min = max(0, remaining / 60)
                
                # Get poll count from collector log
                poll_count = 0
                try:
                    if os.path.exists(str(logs_dir / "collector_stdout.log")):
                        with open(str(logs_dir / "collector_stdout.log"), "r") as f:
                            lines = f.readlines()
                            poll_lines = [l for l in lines if l.startswith("[POLL")]
                            poll_count = len(poll_lines)
                except Exception:
                    pass
                
                # Get request stats from locust log
                total_reqs = "?"
                req_rate = "?"
                try:
                    locust_log_path = logs_dir / "locust_stderr.log"
                    if os.path.exists(str(locust_log_path)):
                        with open(str(locust_log_path), "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            # Find the last aggregated stats line
                            for line in reversed(lines):
                                if "Aggregated" in line and "req/s" in line:
                                    parts = line.split("|")
                                    if len(parts) >= 2:
                                        reqs_part = parts[1].strip().split()
                                        if reqs_part:
                                            total_reqs = reqs_part[0]
                                    if len(parts) >= 8:
                                        rate_part = parts[7].strip().split()
                                        if rate_part:
                                            req_rate = rate_part[0]
                                    break
                except Exception as e:
                    # Silently fail - logs may not be ready yet
                    pass
                
                print(f"\n{'='*70}")
                print(f"  EXPERIMENT STATUS - {time.strftime('%H:%M:%S')}")
                print(f"{'='*70}")
                print(f"  Progress      : [{int(progress_pct):3d}%] {int(elapsed/60)}m {int(elapsed%60):02d}s elapsed")
                print(f"  Remaining     : {int(remaining_min)}m {int(remaining%60):02d}s")
                print(f"  Load Generator: {total_reqs} requests @ {req_rate} req/s")
                print(f"  Collector     : {poll_count} polls completed")
                print(f"  Pattern       : {args.pattern}")
                print(f"  Output CSV    : {output_csv_path}")
                print(f"{'='*70}\n", flush=True)
                
                last_update = current_time
            
            time.sleep(1)
        
        # Wait a bit more for both to finish
        max_wait = 15
        wait_start = time.time()
        while (locust_proc.poll() is None or coll_proc.poll() is None) and (time.time() - wait_start < max_wait):
            time.sleep(0.5)
        
        # Force terminate if still running
        if locust_proc.poll() is None:
            locust_proc.terminate()
            locust_proc.wait(timeout=5)
        if coll_proc.poll() is None:
            coll_proc.terminate()
            coll_proc.wait(timeout=5)
            
        ok(f"Load generator finished (exit code {locust_proc.returncode})")
        ok(f"Metrics collector finished (exit code {coll_proc.returncode})")

    except KeyboardInterrupt:
        warn("Interrupted — stopping child processes...")
        locust_proc.terminate()
        coll_proc.terminate()
        locust_proc.wait(timeout=5)
        coll_proc.wait(timeout=5)

    # ------------------------------------------------------------------
    # 8. Summary
    # ------------------------------------------------------------------
    step("Experiment complete")
    
    # Calculate expected rows
    expected_polls = args.duration * 2  # 2 polls per minute
    expected_services = 7  # front-end, carts, catalogue, orders, payment, shipping, user
    expected_rows = expected_polls * expected_services
    
    # Count actual rows in CSV
    actual_rows = 0
    try:
        if os.path.exists(str(output_csv_path)):
            with open(str(output_csv_path), "r") as f:
                actual_rows = sum(1 for line in f) - 1  # Subtract header
    except Exception:
        pass
    
    ok(f"Metrics CSV    : {output_csv_path}")
    ok(f"Expected rows  : {expected_rows} ({expected_polls} polls × {expected_services} services)")
    ok(f"Actual rows    : {actual_rows}")
    
    if actual_rows == expected_rows:
        ok("✓ Row count matches expected!")
    elif actual_rows > 0:
        warn(f"Row count mismatch (expected {expected_rows}, got {actual_rows})")
    
    ok("Locust log     : output/logs/locust_stdout.log, locust_stderr.log")
    ok("Collector log  : output/logs/collector_stdout.log")

    if not args.skip_docker:
        print()
        print("  To stop the stack when done:")
        print("  docker compose \\")
        print(f"    -f {compose_dir / 'docker-compose.yml'} \\")
        print(f"    -f {compose_dir / 'docker-compose.monitoring.yml'} down")


if __name__ == "__main__":
    main()
