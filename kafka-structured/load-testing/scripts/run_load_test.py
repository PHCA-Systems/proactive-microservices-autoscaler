#!/usr/bin/env python3
"""
Automated Load Test Runner for EuroSys'24 Paper Reproduction
Simplified script to run stochastic load tests with proper configuration.

Usage:
    python run_load_test.py --pattern constant --users 50 --duration 600
    python run_load_test.py --pattern step --host http://localhost:80
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Please ensure locust is installed: pip install locust")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run EuroSys'24 Stochastic Load Tests")
    parser.add_argument("--pattern", choices=["constant", "step", "spike", "ramp", "basic"], 
                       default="basic", help="Load pattern to run")
    parser.add_argument("--users", type=int, default=50, help="Number of users (for basic pattern)")
    parser.add_argument("--spawn-rate", type=int, default=5, help="User spawn rate")
    parser.add_argument("--duration", type=int, default=600, help="Test duration in seconds")
    parser.add_argument("--host", default="http://localhost:80", help="Sock Shop front-end host (default: http://localhost:80)")
    parser.add_argument("--web", action="store_true", help="Launch web interface (default: headless auto-run)")
    parser.add_argument("--csv", help="Export results to CSV file prefix")
    parser.add_argument("--check-deps", action="store_true", help="Check and install dependencies")
    
    args = parser.parse_args()
    
    # Check if locustfile exists in src directory
    if args.pattern == "basic":
        locustfile_path = Path("src/locustfile.py")
        if not locustfile_path.exists():
            print("❌ locustfile.py not found in src/ directory")
            sys.exit(1)
    else:
        locustfile_path = Path(f"src/locustfile_{args.pattern}.py")
        if not locustfile_path.exists():
            print(f"❌ locustfile_{args.pattern}.py not found in src/ directory")
            sys.exit(1)
    
    # Install dependencies if requested
    if args.check_deps:
        print("Installing dependencies...")
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                   "Install Python dependencies")
    
    # Base locust command
    if args.pattern == "basic":
        cmd = [sys.executable, "-m", "locust", "-f", "src/locustfile.py"]
        cmd.extend(["--users", str(args.users), "--spawn-rate", str(args.spawn_rate)])
    else:
        cmd = [sys.executable, "-m", "locust", "-f", f"src/locustfile_{args.pattern}.py"]
        # Add headless mode for automatic execution with paper parameters
        cmd.append("--headless")
        
        # Set pattern-specific parameters based on EuroSys'24 paper
        if args.pattern == "constant":
            # Constant: 50 users for 10 minutes (paper baseline)
            cmd.extend(["--users", "50", "--spawn-rate", "5", "--run-time", "600s"])
            print(f"🚀 Running Constant Load Pattern: 50 users for 10 minutes")
            
        elif args.pattern == "step":
            # Step: Pattern runs automatically with embedded steps
            cmd.extend(["--users", "50", "--spawn-rate", "5", "--run-time", "600s"])
            print(f"🚀 Running Step Load Pattern: 50→200→100→300→50 users over 10 minutes")
            
        elif args.pattern == "spike":
            # Spike: Pattern runs automatically with embedded spikes
            cmd.extend(["--users", "10", "--spawn-rate", "2", "--run-time", "600s"])
            print(f"🚀 Running Spike Load Pattern: Flash crowds with spikes at 1,3,5,7 minutes")
            
        elif args.pattern == "ramp":
            # Ramp: Pattern runs automatically with embedded ramp
            cmd.extend(["--users", "10", "--spawn-rate", "2", "--run-time", "600s"])
            print(f"🚀 Running Ramp Load Pattern: Organic growth 10→150→10 users over 10 minutes")
    
    # Add duration for basic pattern (others already set)
    if args.pattern == "basic" and not args.web:
        cmd.extend(["--run-time", f"{args.duration}s"])
    
    # Add host
    cmd.extend(["--host", args.host])
    
    # Add CSV export if specified
    if args.csv:
        cmd.extend(["--csv", args.csv])
    
    # Add web interface if requested
    if args.web:
        cmd.extend(["--web-host", "0.0.0.0"])
        print(f"🌐 Web interface will be available at http://localhost:8089")
        print(f"📊 Target host: {args.host}")
        print(f"📈 Load pattern: {args.pattern}")
    else:
        print(f"🤖 Running in headless mode with automatic EuroSys'24 paper parameters")
        print(f"📊 Target host: {args.host}")
        print(f"📈 Load pattern: {args.pattern}")
        print(f"⏱️  Duration: 10 minutes (600 seconds)")
        print(f"🎯 Academic Integrity: Purely stochastic with 2s intervals and timeouts")
    
    # Run the test
    success = run_command(cmd, f"Load test ({args.pattern} pattern)")
    
    if success:
        print(f"\n✅ Load test completed successfully!")
        if args.csv:
            print(f"📊 Results exported to {args.csv}_*.csv")
        if not args.web:
            print(f"📈 Pattern: {args.pattern}")
            print(f"🎯 Target: {args.host}")
            print(f"⏱️  Duration: {args.duration}s")
    else:
        print(f"\n❌ Load test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
