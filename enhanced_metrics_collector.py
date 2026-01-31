#!/usr/bin/env python3
"""
Enhanced PHCA Metrics Collector
Collects detailed metrics using Docker API + docker stats
"""

import docker
import subprocess
import time
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List

class EnhancedMetricsCollector:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.target_services = [
            'front-end', 'catalogue', 'catalogue-db', 'carts', 'carts-db',
            'orders', 'orders-db', 'shipping', 'queue-master', 'rabbitmq',
            'payment', 'user', 'user-db', 'edge-router'
        ]
        
        os.makedirs('data', exist_ok=True)
        print(f"🎯 Enhanced PHCA Metrics Collector")
        print(f"📊 Target services: {len(self.target_services)}")
    
    def get_available_metrics(self):
        """Show what metrics are available"""
        print("\n📊 Available Metrics:")
        print("="*50)
        
        # Basic docker stats metrics
        print("✅ BASIC (Current):")
        print("  • CPU percentage")
        print("  • Memory usage/limit")
        print("  • Network I/O total")
        print("  • Block I/O total")
        print("  • Process count")
        
        # Enhanced docker API metrics
        print("\n✅ ENHANCED (Docker API):")
        print("  • Container state (running/stopped/restarting)")
        print("  • Start time / uptime")
        print("  • Exit code (if stopped)")
        print("  • Process ID")
        print("  • Image info")
        print("  • Environment variables")
        print("  • Port mappings")
        print("  • Volume mounts")
        
        # Detailed stats (if available)
        print("\n⚠️  DETAILED (May not work on WSL2):")
        print("  • CPU per core")
        print("  • Memory breakdown (RSS, cache, swap)")
        print("  • Network per interface")
        print("  • Disk I/O per device")
        print("  • Process tree")
        
        # Application-level metrics
        print("\n🔍 APPLICATION-LEVEL (Requires app instrumentation):")
        print("  • HTTP request count/latency")
        print("  • Database connections")
        print("  • Queue lengths")
        print("  • Custom business metrics")
        
        return self._test_metric_availability()
    
    def _test_metric_availability(self):
        """Test which metrics actually work"""
        print(f"\n🧪 Testing metric availability...")
        
        available = {
            'basic_stats': False,
            'docker_api': False,
            'detailed_stats': False,
            'container_logs': False
        }
        
        try:
            # Test basic docker stats
            result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                available['basic_stats'] = True
                print("  ✅ Basic docker stats: Working")
            else:
                print("  ❌ Basic docker stats: Failed")
        except:
            print("  ❌ Basic docker stats: Failed")
        
        try:
            # Test Docker API
            containers = self.docker_client.containers.list()
            if containers:
                available['docker_api'] = True
                print("  ✅ Docker API: Working")
            else:
                print("  ⚠️  Docker API: No containers found")
        except:
            print("  ❌ Docker API: Failed")
        
        try:
            # Test detailed container stats
            container = self.docker_client.containers.get('docker-compose-front-end-1')
            stats = container.stats(stream=False)
            if 'cpu_stats' in stats:
                available['detailed_stats'] = True
                print("  ✅ Detailed container stats: Working")
            else:
                print("  ❌ Detailed container stats: No CPU stats")
        except:
            print("  ❌ Detailed container stats: Failed")
        
        try:
            # Test container logs
            container = self.docker_client.containers.get('docker-compose-front-end-1')
            logs = container.logs(tail=1)
            if logs:
                available['container_logs'] = True
                print("  ✅ Container logs: Working")
            else:
                print("  ⚠️  Container logs: Empty")
        except:
            print("  ❌ Container logs: Failed")
        
        return available
    
    def get_enhanced_container_metrics(self, container_name: str):
        """Get enhanced metrics for a single container"""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Basic container info
            info = {
                'name': container.name,
                'id': container.short_id,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
            }
            
            # Container state details
            if hasattr(container.attrs['State'], 'StartedAt'):
                started_at = container.attrs['State']['StartedAt']
                info['started_at'] = started_at
                
                # Calculate uptime
                if started_at:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = datetime.now(start_time.tzinfo) - start_time
                    info['uptime_seconds'] = uptime.total_seconds()
            
            # Resource limits
            if 'HostConfig' in container.attrs:
                host_config = container.attrs['HostConfig']
                info['memory_limit'] = host_config.get('Memory', 0)
                info['cpu_limit'] = host_config.get('CpuQuota', 0)
            
            # Network info
            if 'NetworkSettings' in container.attrs:
                networks = container.attrs['NetworkSettings']['Networks']
                info['networks'] = list(networks.keys())
                info['ip_addresses'] = [net['IPAddress'] for net in networks.values() if net['IPAddress']]
            
            # Try to get detailed stats
            try:
                stats = container.stats(stream=False)
                
                # CPU details
                if 'cpu_stats' in stats and 'precpu_stats' in stats:
                    cpu_stats = stats['cpu_stats']
                    precpu_stats = stats['precpu_stats']
                    
                    # Calculate CPU percentage more accurately
                    cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
                    system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
                    
                    if system_delta > 0:
                        cpu_percent = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100
                        info['cpu_percent_detailed'] = round(cpu_percent, 2)
                
                # Memory details
                if 'memory_stats' in stats:
                    mem_stats = stats['memory_stats']
                    info['memory_usage_bytes'] = mem_stats.get('usage', 0)
                    info['memory_limit_bytes'] = mem_stats.get('limit', 0)
                    info['memory_cache_bytes'] = mem_stats.get('stats', {}).get('cache', 0)
                    
                    if info['memory_limit_bytes'] > 0:
                        info['memory_percent'] = (info['memory_usage_bytes'] / info['memory_limit_bytes']) * 100
                
                # Network details
                if 'networks' in stats:
                    total_rx = sum(net['rx_bytes'] for net in stats['networks'].values())
                    total_tx = sum(net['tx_bytes'] for net in stats['networks'].values())
                    info['network_rx_bytes'] = total_rx
                    info['network_tx_bytes'] = total_tx
                
                # Block I/O details
                if 'blkio_stats' in stats:
                    blkio = stats['blkio_stats']
                    if 'io_service_bytes_recursive' in blkio:
                        read_bytes = sum(item['value'] for item in blkio['io_service_bytes_recursive'] if item['op'] == 'Read')
                        write_bytes = sum(item['value'] for item in blkio['io_service_bytes_recursive'] if item['op'] == 'Write')
                        info['disk_read_bytes'] = read_bytes
                        info['disk_write_bytes'] = write_bytes
                        
            except Exception as e:
                info['stats_error'] = str(e)
            
            return info
            
        except Exception as e:
            return {'error': str(e), 'container_name': container_name}
    
    def collect_enhanced_metrics(self, duration_minutes: int = 5):
        """Collect enhanced metrics for all containers"""
        print(f"\n📊 Collecting enhanced metrics for {duration_minutes} minutes...")
        
        # Get list of target containers
        containers = []
        for container in self.docker_client.containers.list():
            service_name = self._extract_service_name(container.name)
            if service_name in self.target_services:
                containers.append(container.name)
        
        print(f"📦 Found {len(containers)} target containers")
        
        all_data = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            timestamp = datetime.now()
            
            for container_name in containers:
                metrics = self.get_enhanced_container_metrics(container_name)
                metrics['timestamp'] = timestamp
                metrics['service_name'] = self._extract_service_name(container_name)
                all_data.append(metrics)
            
            # Progress
            elapsed = time.time() - start_time
            remaining = end_time - time.time()
            progress = (elapsed / (duration_minutes * 60)) * 100
            print(f"📊 Progress: {progress:.1f}% | Remaining: {remaining/60:.1f}m", end='\r')
            
            time.sleep(5)
        
        print(f"\n✅ Collection completed!")
        
        # Save to CSV
        if all_data:
            df = pd.DataFrame(all_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/enhanced_metrics_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
            print(f"💾 Enhanced metrics saved to: {filename}")
            print(f"📊 Total records: {len(df)}")
            print(f"📈 Columns: {list(df.columns)}")
            
            return df, filename
        
        return None, None
    
    def _extract_service_name(self, container_name: str) -> str:
        """Extract service name from container name"""
        if container_name.startswith('docker-compose-'):
            name = container_name[15:]
            if name.endswith('-1') or name.endswith('-2') or name.endswith('-3'):
                name = name[:-2]
            return name
        return container_name

def main():
    collector = EnhancedMetricsCollector()
    
    # Show available metrics
    available = collector.get_available_metrics()
    
    # Test enhanced metrics on one container
    print(f"\n🧪 Testing enhanced metrics on front-end container:")
    metrics = collector.get_enhanced_container_metrics('docker-compose-front-end-1')
    
    print(f"\n📊 Sample Enhanced Metrics:")
    for key, value in metrics.items():
        if not key.endswith('_error'):
            print(f"  • {key}: {value}")
    
    # Ask if user wants to collect
    if input(f"\n🚀 Collect enhanced metrics for 2 minutes? (y/N): ").lower().startswith('y'):
        collector.collect_enhanced_metrics(duration_minutes=2)

if __name__ == "__main__":
    main()