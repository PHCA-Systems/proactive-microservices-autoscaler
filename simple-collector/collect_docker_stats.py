"""
Simple Docker Stats Collector
Uses built-in docker stats command - zero setup required
"""

import subprocess
import json
import csv
import time
from datetime import datetime
import threading

class SimpleDockerCollector:
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.running = False
        self.data_file = f"data/{experiment_id}_metrics.csv"
        
        # Create CSV file with headers
        with open(self.data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'container_name', 'service_name', 
                'cpu_percent', 'memory_usage', 'memory_limit', 'memory_percent',
                'network_rx', 'network_tx', 'block_read', 'block_write', 'pids'
            ])
    
    def collect_once(self):
        """Collect metrics once using docker stats"""
        try:
            # Run docker stats command
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                'table {{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error running docker stats: {result.stderr}")
                return
            
            # Parse output
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            timestamp = datetime.now().isoformat()
            
            with open(self.data_file, 'a', newline='') as f:
                writer = csv.writer(f)
                
                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 8:
                        container_id = parts[0]
                        container_name = parts[1]
                        service_name = self._extract_service_name(container_name)
                        
                        # Parse metrics
                        cpu_percent = parts[2].replace('%', '')
                        memory_usage, memory_limit = self._parse_memory(parts[3])
                        memory_percent = parts[4].replace('%', '')
                        network_rx, network_tx = self._parse_network(parts[5])
                        block_read, block_write = self._parse_block_io(parts[6])
                        pids = parts[7]
                        
                        writer.writerow([
                            timestamp, container_name, service_name,
                            cpu_percent, memory_usage, memory_limit, memory_percent,
                            network_rx, network_tx, block_read, block_write, pids
                        ])
            
            print(f"📊 Collected metrics from {len(lines)} containers")
            
        except Exception as e:
            print(f"Error collecting metrics: {e}")
    
    def _extract_service_name(self, container_name: str) -> str:
        """Extract service name from container name"""
        # Remove common suffixes
        name = container_name
        for suffix in ['_1', '_2', '_3']:
            if name.endswith(suffix):
                name = name[:-2]
                break
        
        # Remove common prefixes
        if name.startswith('microservices-demo_'):
            name = name.replace('microservices-demo_', '')
        
        return name
    
    def _parse_memory(self, memory_str: str):
        """Parse memory usage string like '100MiB / 2GiB'"""
        try:
            parts = memory_str.split(' / ')
            usage = self._convert_to_mb(parts[0])
            limit = self._convert_to_mb(parts[1])
            return usage, limit
        except:
            return 0, 0
    
    def _convert_to_mb(self, size_str: str) -> float:
        """Convert size string to MB"""
        size_str = size_str.strip()
        if 'GiB' in size_str:
            return float(size_str.replace('GiB', '')) * 1024
        elif 'MiB' in size_str:
            return float(size_str.replace('MiB', ''))
        elif 'KiB' in size_str:
            return float(size_str.replace('KiB', '')) / 1024
        elif 'B' in size_str:
            return float(size_str.replace('B', '')) / (1024 * 1024)
        return 0
    
    def _parse_network(self, network_str: str):
        """Parse network I/O string like '1.2kB / 800B'"""
        try:
            parts = network_str.split(' / ')
            rx = self._convert_to_bytes(parts[0])
            tx = self._convert_to_bytes(parts[1])
            return rx, tx
        except:
            return 0, 0
    
    def _parse_block_io(self, block_str: str):
        """Parse block I/O string like '1.2MB / 0B'"""
        try:
            parts = block_str.split(' / ')
            read = self._convert_to_bytes(parts[0])
            write = self._convert_to_bytes(parts[1])
            return read, write
        except:
            return 0, 0
    
    def _convert_to_bytes(self, size_str: str) -> float:
        """Convert size string to bytes"""
        size_str = size_str.strip()
        if 'GB' in size_str:
            return float(size_str.replace('GB', '')) * 1e9
        elif 'MB' in size_str:
            return float(size_str.replace('MB', '')) * 1e6
        elif 'kB' in size_str:
            return float(size_str.replace('kB', '')) * 1e3
        elif 'B' in size_str:
            return float(size_str.replace('B', ''))
        return 0
    
    def start_collection(self, interval_seconds: int = 5):
        """Start continuous collection"""
        self.running = True
        print(f"🔄 Starting collection every {interval_seconds}s")
        print(f"📁 Data will be saved to: {self.data_file}")
        
        while self.running:
            self.collect_once()
            time.sleep(interval_seconds)
        
        print("✅ Collection stopped")
    
    def stop_collection(self):
        """Stop collection"""
        self.running = False

if __name__ == "__main__":
    import os
    import signal
    import sys
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Create collector
    experiment_id = f"simple_experiment_{int(time.time())}"
    collector = SimpleDockerCollector(experiment_id)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n🛑 Stopping collection...")
        collector.stop_collection()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start collection
    collector.start_collection(interval_seconds=5)