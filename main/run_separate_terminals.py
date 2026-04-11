#!/usr/bin/env python3
"""
Run Load Test and Metrics Collection in Separate Terminals
Opens separate PowerShell windows for each task
"""

import subprocess
import time
import os
from datetime import datetime

class SeparateTerminalRunner:
    def __init__(self, sock_shop_url=None, use_k8s=False):
        self.use_k8s = use_k8s
        if use_k8s:
            # For K8s, URL will be auto-detected by the locustfile
            self.sock_shop_url = sock_shop_url or "auto-detect"
        else:
            # For Docker, use localhost:80 as default
            self.sock_shop_url = sock_shop_url or "http://localhost:80"
        
    def update_locustfile_url(self, pattern, url):
        """Update the host URL in locustfile (only for non-K8s versions)"""
        if self.use_k8s:
            # K8s versions auto-detect URL, no need to update
            print(f"✅ Using K8s version with auto-detection for {pattern} pattern")
            return True
            
        locustfile_path = f"load-testing/src/locustfile_{pattern}.py"
        
        if not os.path.exists(locustfile_path):
            print(f"❌ Locustfile not found: {locustfile_path}")
            return False
        
        try:
            # Read the file
            with open(locustfile_path, 'r') as f:
                content = f.read()
            
            # Update the host line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'host =' in line and ('localhost' in line or '127.0.0.1' in line):
                    lines[i] = f'    host = "{url}"'
                    break
            
            # Write back
            with open(locustfile_path, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"✅ Updated {locustfile_path} with URL: {url}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating locustfile: {e}")
            return False
    
    def start_metrics_terminal(self, duration, interval=10):
        """Start metrics collection in separate PowerShell terminal"""
        print("📊 Starting metrics collection terminal...")
        
        # Create PowerShell command to run metrics collection
        ps_command = f"""
        cd '{os.getcwd()}';
        phca_venv\\Scripts\\activate;
        python collect_per_service_metrics.py --interval {interval} --duration {duration + 30};
        Write-Host 'Metrics collection completed. Press any key to close...';
        Read-Host
        """
        
        try:
            # Start PowerShell in new window
            subprocess.Popen([
                'powershell.exe', 
                '-NoExit',
                '-Command', ps_command
            ], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            print("✅ Metrics collection terminal started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting metrics terminal: {e}")
            return False
    
    def start_load_test_terminal(self, pattern, duration):
        """Start load test in separate PowerShell terminal"""
        print(f"🚀 Starting load test terminal ({pattern} pattern)...")
        
        # Choose the appropriate locustfile based on K8s flag
        if self.use_k8s:
            locustfile = f"src/k8s/locustfile_{pattern}_k8s.py"
            print(f"📋 Using K8s version: {locustfile}")
        else:
            locustfile = f"src/locustfile_{pattern}.py"
            print(f"📋 Using Docker version: {locustfile}")
        
        # Create PowerShell command to run load test directly with locust
        if self.use_k8s:
            ps_command = f"""
            cd '{os.getcwd()}\\load-testing';
            ..\\phca_venv\\Scripts\\activate;
            python -m locust -f {locustfile} --headless --users 50 --spawn-rate 5 --run-time {duration}s;
            Write-Host 'Load test completed. Press any key to close...';
            Read-Host
            """
        else:
            ps_command = f"""
            cd '{os.getcwd()}\\load-testing';
            ..\\phca_venv\\Scripts\\activate;
            python -m locust -f {locustfile} --headless --users 50 --spawn-rate 5 --run-time {duration}s --host {self.sock_shop_url};
            Write-Host 'Load test completed. Press any key to close...';
            Read-Host
            """
        
        try:
            # Start PowerShell in new window
            subprocess.Popen([
                'powershell.exe', 
                '-NoExit',
                '-Command', ps_command
            ], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            print("✅ Load test terminal started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting load test terminal: {e}")
            return False
    
    def run_combined_test(self, pattern='constant', duration=300, metrics_interval=10):
        """Run load test and metrics collection in separate terminals"""
        deployment_type = "Kubernetes" if self.use_k8s else "Docker"
        print(f"🎯 PHCA Load Test with Per-Service Metrics (Separate Terminals)")
        print("=" * 70)
        print(f"🏗️  Deployment: {deployment_type}")
        print(f"📊 Pattern: {pattern}")
        print(f"⏱️  Duration: {duration} seconds")
        print(f"📈 Metrics interval: {metrics_interval} seconds")
        if not self.use_k8s:
            print(f"🎯 Target: {self.sock_shop_url}")
        else:
            print(f"🎯 Target: Auto-detected from minikube service")
        print()
        
        # Update locustfile with correct URL (only for Docker versions)
        if not self.update_locustfile_url(pattern, self.sock_shop_url):
            print("❌ Failed to update locustfile URL")
            return False
        
        print("🚀 Starting separate terminals...")
        print()
        
        # Start metrics collection terminal
        metrics_success = self.start_metrics_terminal(duration, metrics_interval)
        if not metrics_success:
            print("❌ Failed to start metrics collection terminal")
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Start load test terminal
        load_test_success = self.start_load_test_terminal(pattern, duration)
        if not load_test_success:
            print("❌ Failed to start load test terminal")
            return False
        
        print("✅ Both terminals started successfully!")
        print()
        print("📋 What's happening:")
        print("  🔹 Terminal 1: Collecting per-service metrics every", metrics_interval, "seconds")
        print("  🔹 Terminal 2: Running", pattern, "load test for", duration, "seconds")
        if self.use_k8s:
            print("  🔹 K8s version: Auto-detecting Sock Shop URL from minikube")
        print()
        print("📁 Results will be saved to:")
        print("  🔹 Metrics: results/per_service_metrics_*.csv")
        print("  🔹 Load test: load-testing directory")
        print()
        print("⏳ Tests are running in separate windows...")
        print("💡 You can monitor progress in each terminal window")
        
        return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load test and metrics in separate terminals")
    parser.add_argument("--pattern", choices=["constant", "step", "spike", "ramp"], 
                       default="constant", help="Load test pattern")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--metrics-interval", type=int, default=10, help="Metrics collection interval")
    parser.add_argument("--url", help="Sock Shop URL (for Docker deployment)", default="http://localhost:80")
    parser.add_argument("--k8s", action="store_true", help="Use Kubernetes deployment with auto URL detection")
    
    args = parser.parse_args()
    
    # Create runner
    runner = SeparateTerminalRunner(args.url, use_k8s=args.k8s)
    
    # Run combined test
    success = runner.run_combined_test(
        pattern=args.pattern,
        duration=args.duration,
        metrics_interval=args.metrics_interval
    )
    
    if success:
        print("🎉 Setup completed! Check the separate terminal windows.")
    else:
        print("❌ Setup failed!")

if __name__ == "__main__":
    main()