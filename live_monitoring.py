#!/usr/bin/env python3
"""
Live Monitoring During Load Testing
Shows real-time metrics while load test is running
"""

import subprocess
import time
import os
from datetime import datetime
from influxdb_client import InfluxDBClient

class LiveMonitor:
    def __init__(self):
        self.client = InfluxDBClient(
            url="http://localhost:8086",
            token="phca-token-12345",
            org="phca"
        )
        self.query_api = self.client.query_api()
    
    def get_latest_metrics(self):
        """Get latest metrics from InfluxDB"""
        try:
            query = '''
            from(bucket: "microservices")
              |> range(start: -2m)
              |> filter(fn: (r) => r["_measurement"] == "container_metrics")
              |> filter(fn: (r) => r["_field"] == "cpu_percent" or r["_field"] == "memory_usage_percent")
              |> group(columns: ["service_name", "_field"])
              |> last()
            '''
            
            result = self.query_api.query(org="phca", query=query)
            
            metrics = {}
            for table in result:
                for record in table.records:
                    service = record.values.get("service_name")
                    field = record.values.get("_field")
                    value = record.get_value()
                    timestamp = record.get_time()
                    
                    if service not in metrics:
                        metrics[service] = {}
                    metrics[service][field] = {
                        'value': value,
                        'time': timestamp
                    }
            
            return metrics
        except Exception as e:
            print(f"❌ Error getting metrics: {e}")
            return {}
    
    def get_docker_stats(self):
        """Get current Docker stats"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                '{{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                stats = {}
                for line in result.stdout.strip().split('\n'):
                    if 'docker-compose' in line:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            name = parts[0].replace('docker-compose-', '').replace('-1', '')
                            cpu = float(parts[1].replace('%', ''))
                            mem = float(parts[2].replace('%', ''))
                            stats[name] = {'cpu': cpu, 'mem': mem}
                return stats
            return {}
        except Exception as e:
            print(f"❌ Error getting Docker stats: {e}")
            return {}
    
    def display_metrics(self, influx_metrics, docker_stats):
        """Display metrics in a nice format"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🎯 PHCA Live Monitoring - Metrics Under Load")
        print("=" * 70)
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | 🔄 Refreshing every 10 seconds")
        print("=" * 70)
        
        # Combine data
        all_services = set(influx_metrics.keys()) | set(docker_stats.keys())
        
        if not all_services:
            print("⚠️  No metrics available yet...")
            return
        
        print(f"{'Service':<15} {'CPU %':<8} {'Memory %':<10} {'Source':<10}")
        print("-" * 50)
        
        # Sort services by CPU usage (highest first)
        services_by_cpu = []
        for service in all_services:
            cpu_val = 0
            if service in docker_stats:
                cpu_val = docker_stats[service]['cpu']
            elif service in influx_metrics and 'cpu_percent' in influx_metrics[service]:
                cpu_val = influx_metrics[service]['cpu_percent']['value']
            services_by_cpu.append((service, cpu_val))
        
        services_by_cpu.sort(key=lambda x: x[1], reverse=True)
        
        for service, _ in services_by_cpu:
            # Get CPU
            if service in docker_stats:
                cpu = f"{docker_stats[service]['cpu']:.2f}"
                mem = f"{docker_stats[service]['mem']:.2f}"
                source = "Docker"
            elif service in influx_metrics:
                cpu_data = influx_metrics[service].get('cpu_percent', {})
                mem_data = influx_metrics[service].get('memory_usage_percent', {})
                cpu = f"{cpu_data.get('value', 0):.2f}" if cpu_data else "0.00"
                mem = f"{mem_data.get('value', 0):.2f}" if mem_data else "0.00"
                source = "InfluxDB"
            else:
                cpu = "0.00"
                mem = "0.00"
                source = "N/A"
            
            print(f"{service:<15} {cpu:<8} {mem:<10} {source:<10}")
        
        print("\n" + "=" * 70)
        print("🔥 Top CPU Users:")
        top_services = [s for s, cpu in services_by_cpu[:3] if cpu > 0]
        for i, service in enumerate(top_services, 1):
            cpu_val = next(cpu for s, cpu in services_by_cpu if s == service)
            print(f"  {i}. {service}: {cpu_val:.2f}% CPU")
        
        print(f"\n📊 Total Services Monitored: {len(all_services)}")
        print("💡 Press Ctrl+C to stop monitoring")
    
    def run(self, refresh_interval=10):
        """Run live monitoring"""
        print("🚀 Starting live monitoring...")
        print("💡 Make sure load test is running for best results")
        
        try:
            while True:
                # Get metrics from both sources
                influx_metrics = self.get_latest_metrics()
                docker_stats = self.get_docker_stats()
                
                # Display
                self.display_metrics(influx_metrics, docker_stats)
                
                # Wait
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        finally:
            self.client.close()

def main():
    """Main function"""
    monitor = LiveMonitor()
    monitor.run()

if __name__ == "__main__":
    main()