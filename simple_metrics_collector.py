#!/usr/bin/env python3
"""
Simple PHCA Metrics Collector
Reliable Docker stats-based metrics collection for microservices research
"""

import subprocess
import time
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List

class SimpleMetricsCollector:
    def __init__(self):
        # Sock Shop services we want to monitor
        self.target_services = [
            'front-end', 'catalogue', 'catalogue-db', 'carts', 'carts-db',
            'orders', 'orders-db', 'shipping', 'queue-master', 'rabbitmq',
            'payment', 'user', 'user-db', 'edge-router'
        ]
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        print(f"🎯 Simple PHCA Metrics Collector")
        print(f"📊 Target services: {len(self.target_services)}")
    
    def get_docker_containers(self):
        """Get running Docker containers using docker stats"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                '{{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                containers = []
                
                for line in lines:
                    if line.strip() and 'docker-compose' in line:
                        parts = [p.strip() for p in line.split('\t') if p.strip()]
                        
                        if len(parts) >= 6:
                            container_id = parts[0]
                            name = parts[1]
                            cpu_percent = parts[2]
                            memory_usage = parts[3]
                            network_io = parts[4]
                            block_io = parts[5]
                            
                            service_name = self._extract_service_name(name)
                            if service_name in self.target_services:
                                containers.append({
                                    'container_id': container_id,
                                    'name': name,
                                    'service_name': service_name,
                                    'cpu_percent': cpu_percent,
                                    'memory_usage': memory_usage,
                                    'network_io': network_io,
                                    'block_io': block_io
                                })
                
                return containers
            else:
                print(f"❌ Docker stats error: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting Docker containers: {e}")
            return []
    
    def _extract_service_name(self, container_name: str) -> str:
        """Extract service name from Docker container name"""
        if container_name.startswith('docker-compose-'):
            name = container_name[15:]  # Remove 'docker-compose-'
            if name.endswith('-1') or name.endswith('-2') or name.endswith('-3'):
                name = name[:-2]
            return name
        return container_name
    
    def _parse_cpu_percent(self, cpu_str: str) -> float:
        """Parse CPU percentage from Docker stats"""
        try:
            return float(cpu_str.replace('%', ''))
        except:
            return 0.0
    
    def collect_metrics(self, duration_minutes: int = 10, experiment_id: str = None):
        """Collect metrics for specified duration"""
        
        if not experiment_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_id = f"simple_experiment_{timestamp}"
        
        print(f"📊 Collecting metrics for experiment: {experiment_id}")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        
        # Check containers
        containers = self.get_docker_containers()
        if not containers:
            print("❌ No Sock Shop containers found!")
            return None, None
        
        print(f"📦 Found {len(containers)} containers")
        
        # Collect data
        all_data = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        print(f"🚀 Starting data collection...")
        
        while time.time() < end_time:
            timestamp = datetime.now()
            containers = self.get_docker_containers()
            
            for container in containers:
                data_point = {
                    'timestamp': timestamp,
                    'experiment_id': experiment_id,
                    'service_name': container['service_name'],
                    'container_name': container['name'],
                    'container_id': container['container_id'],
                    'cpu_percent': self._parse_cpu_percent(container['cpu_percent']),
                    'memory_usage': container['memory_usage'],
                    'network_io': container['network_io'],
                    'block_io': container['block_io']
                }
                all_data.append(data_point)
            
            # Progress indicator
            elapsed = time.time() - start_time
            remaining = end_time - time.time()
            progress = (elapsed / (duration_minutes * 60)) * 100
            
            print(f"📊 Progress: {progress:.1f}% | Containers: {len(containers)} | Remaining: {remaining/60:.1f}m", end='\r')
            
            # Wait 5 seconds before next collection
            time.sleep(5)
        
        print(f"\n✅ Data collection completed!")
        
        # Convert to DataFrame and save
        if all_data:
            df = pd.DataFrame(all_data)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/simple_metrics_{experiment_id}_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
            print(f"💾 Data saved to: {filename}")
            print(f"📊 Total records: {len(df)}")
            print(f"🎯 Services monitored: {df['service_name'].nunique()}")
            print(f"⏱️  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df, filename
        else:
            print("❌ No metrics data collected!")
            return None, None
    
    def get_service_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate summary statistics for each service"""
        numeric_columns = ['cpu_percent']
        
        if len(numeric_columns) > 0:
            summary = df.groupby('service_name')[numeric_columns].agg(['mean', 'std', 'min', 'max', 'count']).round(2)
            return summary
        else:
            return pd.DataFrame()

def main():
    """Main function"""
    collector = SimpleMetricsCollector()
    
    # Check what containers are available
    containers = collector.get_docker_containers()
    if containers:
        print(f"\n📦 Found {len(containers)} Sock Shop containers:")
        for container in containers:
            print(f"  • {container['service_name']} - CPU: {container['cpu_percent']} - Memory: {container['memory_usage']}")
    else:
        print("\n❌ No Sock Shop containers found!")
        print("💡 Make sure Sock Shop is running:")
        print("   cd microservices-demo")
        print("   docker-compose up -d")
        return
    
    print(f"\n🎯 Simple Metrics Collector Ready!")
    print(f"📊 Use: collector.collect_metrics(duration_minutes=5)")

if __name__ == "__main__":
    main()