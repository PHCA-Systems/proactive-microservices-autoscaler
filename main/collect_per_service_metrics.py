#!/usr/bin/env python3
"""
Per-Service Metrics Collector for PHCA Research
Collects CPU and memory usage for each Sock Shop microservice
"""

import subprocess
import json
import csv
import time
from datetime import datetime
import os

class PerServiceMetricsCollector:
    def __init__(self, output_dir="results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize CSV file
        self.csv_file = os.path.join(output_dir, f"per_service_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.init_csv()
    
    def init_csv(self):
        """Initialize CSV file with headers"""
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'service_name', 'cpu_cores', 'memory_bytes', 
                'cpu_millicores', 'memory_mb', 'memory_gb'
            ])
    
    def get_pod_metrics(self):
        """Get metrics using kubectl top pods"""
        try:
            result = subprocess.run(
                ['kubectl', 'top', 'pods', '-n', 'sock-shop', '--no-headers'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                print(f"Error getting pod metrics: {result.stderr}")
                return []
            
            metrics = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        pod_name = parts[0]
                        cpu_str = parts[1]  # e.g., "2m" or "70m"
                        memory_str = parts[2]  # e.g., "335Mi" or "123Mi"
                        
                        # Extract service name from pod name
                        service_name = pod_name.split('-')[0]  # e.g., "carts-b6c5c87f9-5b94l" -> "carts"
                        
                        # Parse CPU (millicores)
                        cpu_millicores = int(cpu_str.replace('m', ''))
                        cpu_cores = cpu_millicores / 1000.0
                        
                        # Parse Memory (bytes)
                        if memory_str.endswith('Mi'):
                            memory_mb = int(memory_str.replace('Mi', ''))
                            memory_bytes = memory_mb * 1024 * 1024
                        elif memory_str.endswith('Gi'):
                            memory_gb = int(memory_str.replace('Gi', ''))
                            memory_bytes = memory_gb * 1024 * 1024 * 1024
                            memory_mb = memory_gb * 1024
                        else:
                            # Assume bytes
                            memory_bytes = int(memory_str)
                            memory_mb = memory_bytes / (1024 * 1024)
                        
                        memory_gb = memory_bytes / (1024 * 1024 * 1024)
                        
                        metrics.append({
                            'service_name': service_name,
                            'pod_name': pod_name,
                            'cpu_cores': cpu_cores,
                            'cpu_millicores': cpu_millicores,
                            'memory_bytes': memory_bytes,
                            'memory_mb': memory_mb,
                            'memory_gb': memory_gb
                        })
            
            return metrics
            
        except Exception as e:
            print(f"Error collecting metrics: {e}")
            return []
    
    def collect_and_save(self):
        """Collect metrics and save to CSV"""
        timestamp = datetime.now().isoformat()
        metrics = self.get_pod_metrics()
        
        if not metrics:
            print("No metrics collected")
            return
        
        # Save to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for metric in metrics:
                writer.writerow([
                    timestamp,
                    metric['service_name'],
                    metric['cpu_cores'],
                    metric['memory_bytes'],
                    metric['cpu_millicores'],
                    metric['memory_mb'],
                    metric['memory_gb']
                ])
        
        # Print summary
        print(f"📊 Collected metrics at {timestamp}")
        print("Per-Service Resource Usage:")
        print("-" * 50)
        
        # Sort by CPU usage
        metrics.sort(key=lambda x: x['cpu_millicores'], reverse=True)
        
        for metric in metrics:
            print(f"  {metric['service_name']:15} | CPU: {metric['cpu_millicores']:3d}m | Memory: {metric['memory_mb']:6.1f}MB")
        
        total_cpu = sum(m['cpu_millicores'] for m in metrics)
        total_memory = sum(m['memory_mb'] for m in metrics)
        
        print("-" * 50)
        print(f"  {'TOTAL':15} | CPU: {total_cpu:3d}m | Memory: {total_memory:6.1f}MB")
        print(f"📁 Data saved to: {self.csv_file}")
    
    def continuous_collection(self, interval=15, duration=300):
        """Collect metrics continuously"""
        print(f"🚀 Starting continuous collection:")
        print(f"   Interval: {interval} seconds")
        print(f"   Duration: {duration} seconds")
        print(f"   Output: {self.csv_file}")
        print()
        
        start_time = time.time()
        collection_count = 0
        
        while time.time() - start_time < duration:
            self.collect_and_save()
            collection_count += 1
            
            remaining = duration - (time.time() - start_time)
            if remaining > interval:
                print(f"⏱️  Next collection in {interval}s (remaining: {remaining:.0f}s)")
                time.sleep(interval)
            else:
                break
        
        print(f"\n✅ Collection completed!")
        print(f"   Collections: {collection_count}")
        print(f"   Duration: {time.time() - start_time:.1f} seconds")
        print(f"   File: {self.csv_file}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect per-service metrics from Kubernetes")
    parser.add_argument("--interval", type=int, default=15, help="Collection interval in seconds")
    parser.add_argument("--duration", type=int, default=300, help="Total duration in seconds")
    parser.add_argument("--once", action="store_true", help="Collect once and exit")
    
    args = parser.parse_args()
    
    collector = PerServiceMetricsCollector()
    
    if args.once:
        collector.collect_and_save()
    else:
        collector.continuous_collection(args.interval, args.duration)

if __name__ == "__main__":
    main()