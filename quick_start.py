"""
Quick Start Script for PHCA Metrics Collection
This bypasses complex setup and gets you collecting data immediately
"""

import subprocess
import time
import csv
import json
from datetime import datetime
import os
import threading
import signal
import sys

class QuickMetricsCollector:
    def __init__(self):
        self.running = False
        self.data_file = None
        
    def collect_docker_metrics(self, experiment_id="quick_test"):
        """Collect metrics using docker stats command"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_file = f"data/quick_{experiment_id}_{timestamp}.csv"
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Create CSV file with headers
        with open(self.data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'container_name', 'service_name', 
                'cpu_percent', 'memory_usage_mb', 'memory_limit_mb', 'memory_percent',
                'network_rx_mb', 'network_tx_mb', 'pids'
            ])
        
        print(f"🚀 Starting metrics collection...")
        print(f"📁 Data will be saved to: {self.data_file}")
        print(f"⏹️  Press Ctrl+C to stop")
        
        self.running = True
        
        while self.running:
            try:
                # Get docker stats
                result = subprocess.run([
                    'docker', 'stats', '--no-stream', '--format', 
                    '{{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.PIDs}}'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')  # No header to skip
                    current_time = datetime.now().isoformat()
                    
                    # Filter for Sock Shop containers
                    sock_shop_containers = []
                    for line in lines:
                        if 'docker-compose-' in line and any(service in line.lower() for service in [
                            'front-end', 'catalogue', 'carts', 'orders', 
                            'shipping', 'payment', 'user', 'rabbitmq', 'queue-master', 'edge-router'
                        ]):
                            sock_shop_containers.append(line)
                    
                    if sock_shop_containers:
                        with open(self.data_file, 'a', newline='') as f:
                            writer = csv.writer(f)
                            
                            for line in sock_shop_containers:
                                # Split by comma (CSV format)
                                parts = line.split(',')
                                if len(parts) >= 7:
                                    container_id = parts[0]
                                    container_name = parts[1]
                                    service_name = self._extract_service_name(container_name)
                                    
                                    # Parse metrics
                                    cpu_percent = float(parts[2].replace('%', ''))
                                    memory_usage_mb, memory_limit_mb = self._parse_memory(parts[3])
                                    memory_percent = float(parts[4].replace('%', ''))
                                    network_rx_mb, network_tx_mb = self._parse_network(parts[5])
                                    pids = int(parts[6]) if parts[6].isdigit() else 0
                                    
                                    writer.writerow([
                                        current_time, container_name, service_name,
                                        cpu_percent, memory_usage_mb, memory_limit_mb, memory_percent,
                                        network_rx_mb, network_tx_mb, pids
                                    ])
                        
                        print(f"📊 Collected metrics from {len(sock_shop_containers)} containers at {current_time}")
                    else:
                        print("⚠️  No Sock Shop containers found")
                
                time.sleep(5)  # Collect every 5 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(5)
        
        self.running = False
        print(f"\n✅ Metrics collection stopped")
        print(f"📊 Data saved to: {self.data_file}")
        
        return self.data_file
    
    def _extract_service_name(self, container_name):
        """Extract service name from container name"""
        name = container_name.lower()
        
        # Remove common prefixes/suffixes
        for prefix in ['docker-compose-', 'microservices-demo-']:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        for suffix in ['-1', '-2', '-3']:
            if name.endswith(suffix):
                name = name[:-2]
        
        return name
    
    def _parse_memory(self, memory_str):
        """Parse memory usage string like '100MiB / 2GiB'"""
        try:
            parts = memory_str.split(' / ')
            usage = self._convert_to_mb(parts[0])
            limit = self._convert_to_mb(parts[1])
            return usage, limit
        except:
            return 0, 0
    
    def _convert_to_mb(self, size_str):
        """Convert size string to MB"""
        size_str = size_str.strip()
        if 'GiB' in size_str or 'GB' in size_str:
            return float(size_str.replace('GiB', '').replace('GB', '')) * 1024
        elif 'MiB' in size_str or 'MB' in size_str:
            return float(size_str.replace('MiB', '').replace('MB', ''))
        elif 'KiB' in size_str or 'KB' in size_str:
            return float(size_str.replace('KiB', '').replace('KB', '')) / 1024
        elif 'B' in size_str:
            return float(size_str.replace('B', '')) / (1024 * 1024)
        return 0
    
    def _parse_network(self, network_str):
        """Parse network I/O string like '1.2kB / 800B'"""
        try:
            parts = network_str.split(' / ')
            rx = self._convert_to_mb(parts[0])
            tx = self._convert_to_mb(parts[1])
            return rx, tx
        except:
            return 0, 0
    
    def stop(self):
        """Stop collection"""
        self.running = False

def run_load_test_simple(duration_seconds=300):
    """Run a simple load test"""
    print(f"🔥 Starting load test for {duration_seconds} seconds...")
    
    try:
        # Run locust
        cmd = [
            'locust',
            '-f', 'load-testing/src/locustfile.py',
            '--host', 'http://localhost:80',
            '--headless',
            '--users', '25',
            '--spawn-rate', '5',
            '--run-time', f'{duration_seconds}s'
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in process.stdout:
            if line.strip():
                print(f"🔥 {line.strip()}")
        
        process.wait()
        print("✅ Load test completed")
        
    except Exception as e:
        print(f"❌ Load test error: {e}")

def main():
    """Main function with simple menu"""
    
    print("🎯 PHCA Quick Start")
    print("=" * 50)
    print("1. Collect metrics only (5 minutes)")
    print("2. Run load test only (5 minutes)")  
    print("3. Run both metrics + load test (5 minutes)")
    print("4. Custom duration")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        # Metrics only
        collector = QuickMetricsCollector()
        try:
            collector.collect_docker_metrics("metrics_only")
        except KeyboardInterrupt:
            collector.stop()
    
    elif choice == "2":
        # Load test only
        run_load_test_simple(300)
    
    elif choice == "3":
        # Both
        collector = QuickMetricsCollector()
        
        # Start metrics collection in background
        metrics_thread = threading.Thread(target=collector.collect_docker_metrics, args=("full_test",))
        metrics_thread.daemon = True
        metrics_thread.start()
        
        # Wait a moment then start load test
        time.sleep(5)
        
        try:
            run_load_test_simple(300)
        except KeyboardInterrupt:
            pass
        finally:
            collector.stop()
            metrics_thread.join(timeout=10)
    
    elif choice == "4":
        # Custom duration
        try:
            duration = int(input("Enter duration in seconds: "))
            collector = QuickMetricsCollector()
            
            # Start metrics collection in background
            metrics_thread = threading.Thread(target=collector.collect_docker_metrics, args=(f"custom_{duration}s",))
            metrics_thread.daemon = True
            metrics_thread.start()
            
            # Wait a moment then start load test
            time.sleep(5)
            
            try:
                run_load_test_simple(duration)
            except KeyboardInterrupt:
                pass
            finally:
                collector.stop()
                metrics_thread.join(timeout=10)
        
        except ValueError:
            print("❌ Invalid duration")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Stopping...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    main()