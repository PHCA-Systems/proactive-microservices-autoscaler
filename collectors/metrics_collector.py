#!/usr/bin/env python3
"""
PHCA Metrics Collector
Unified metrics collection for microservices autoscaling research
Supports CSV and InfluxDB output with live monitoring
"""

import subprocess
import time
import os
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Optional InfluxDB support
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

class PHCAMetricsCollector:
    def __init__(self, output_type="csv", output_file=None, influx_config=None):
        """
        Initialize PHCA Metrics Collector
        
        Args:
            output_type: "csv" or "influxdb"
            output_file: CSV file path (for CSV output)
            influx_config: InfluxDB configuration dict
        """
        self.output_type = output_type
        self.output_file = output_file
        
        # Sock Shop services to monitor
        self.target_services = [
            'front-end', 'catalogue', 'catalogue-db', 'carts', 'carts-db',
            'orders', 'orders-db', 'shipping', 'queue-master', 'rabbitmq',
            'payment', 'user', 'user-db', 'edge-router'
        ]
        
        # InfluxDB setup
        self.influx_client = None
        self.write_api = None
        if output_type == "influxdb":
            if not INFLUXDB_AVAILABLE:
                raise ImportError("InfluxDB client not available. Install: pip install influxdb-client")
            self._setup_influxdb(influx_config or {})
        
        # CSV setup
        self.csv_data = []
        
        print(f"🎯 PHCA Metrics Collector")
        print(f"📊 Target services: {len(self.target_services)}")
        print(f"💾 Output: {output_type}")
        if output_type == "csv":
            print(f"📄 File: {output_file}")
        elif output_type == "influxdb":
            print(f"🗄️  Database: {influx_config.get('url', 'http://localhost:8086')}")
    
    def _setup_influxdb(self, config):
        """Setup InfluxDB connection"""
        self.influx_url = config.get('url', 'http://localhost:8086')
        self.token = config.get('token', 'phca-token-12345')
        self.org = config.get('org', 'phca')
        self.bucket = config.get('bucket', 'microservices')
        
        try:
            self.influx_client = InfluxDBClient(url=self.influx_url, token=self.token, org=self.org)
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            
            # Test connection
            health = self.influx_client.health()
            if health.status == "pass":
                print("✅ InfluxDB connection successful")
            else:
                raise Exception(f"InfluxDB health check failed: {health.status}")
        except Exception as e:
            print(f"❌ InfluxDB connection failed: {e}")
            raise
    
    def get_container_metrics(self):
        """Get metrics from all target containers"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                '{{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"❌ Docker stats error: {result.stderr}")
                return []
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and 'docker-compose' in line:
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    
                    if len(parts) >= 6:
                        container_id = parts[0]
                        name = parts[1]
                        cpu_percent = parts[2]
                        memory_usage = parts[3]
                        network_io = parts[4]
                        block_io = parts[5]
                        pids = parts[6] if len(parts) > 6 else "0"
                        
                        service_name = self._extract_service_name(name)
                        if service_name in self.target_services:
                            containers.append({
                                'timestamp': datetime.now(),
                                'container_id': container_id,
                                'container_name': name,
                                'service_name': service_name,
                                'cpu_percent': self._parse_cpu_percent(cpu_percent),
                                'memory_usage_bytes': self._parse_memory_bytes(memory_usage),
                                'memory_limit_bytes': self._parse_memory_limit(memory_usage),
                                'memory_usage_percent': self._calculate_memory_percent(memory_usage),
                                'network_rx_bytes': self._parse_network_rx(network_io),
                                'network_tx_bytes': self._parse_network_tx(network_io),
                                'block_read_bytes': self._parse_block_read(block_io),
                                'block_write_bytes': self._parse_block_write(block_io),
                                'pids': int(pids) if pids.isdigit() else 0
                            })
            
            return containers
            
        except Exception as e:
            print(f"❌ Error getting container metrics: {e}")
            return []
    
    def _extract_service_name(self, container_name: str) -> str:
        """Extract service name from container name"""
        if container_name.startswith('docker-compose-'):
            name = container_name[15:]
            if name.endswith('-1') or name.endswith('-2') or name.endswith('-3'):
                name = name[:-2]
            return name
        return container_name
    
    def _parse_cpu_percent(self, cpu_str: str) -> float:
        """Parse CPU percentage"""
        try:
            return float(cpu_str.replace('%', ''))
        except:
            return 0.0
    
    def _parse_memory_bytes(self, mem_str: str) -> int:
        """Parse memory usage in bytes"""
        try:
            usage_part = mem_str.split(' / ')[0].strip()
            return self._convert_to_bytes(usage_part)
        except:
            return 0
    
    def _parse_memory_limit(self, mem_str: str) -> int:
        """Parse memory limit in bytes"""
        try:
            limit_part = mem_str.split(' / ')[1].strip()
            return self._convert_to_bytes(limit_part)
        except:
            return 0
    
    def _calculate_memory_percent(self, mem_str: str) -> float:
        """Calculate memory usage percentage"""
        try:
            usage = self._parse_memory_bytes(mem_str)
            limit = self._parse_memory_limit(mem_str)
            return (usage / limit * 100) if limit > 0 else 0
        except:
            return 0
    
    def _parse_network_rx(self, net_str: str) -> int:
        """Parse network received bytes"""
        try:
            rx_part = net_str.split(' / ')[0].strip()
            return self._convert_to_bytes(rx_part)
        except:
            return 0
    
    def _parse_network_tx(self, net_str: str) -> int:
        """Parse network transmitted bytes"""
        try:
            tx_part = net_str.split(' / ')[1].strip()
            return self._convert_to_bytes(tx_part)
        except:
            return 0
    
    def _parse_block_read(self, block_str: str) -> int:
        """Parse block read bytes"""
        try:
            read_part = block_str.split(' / ')[0].strip()
            return self._convert_to_bytes(read_part)
        except:
            return 0
    
    def _parse_block_write(self, block_str: str) -> int:
        """Parse block write bytes"""
        try:
            write_part = block_str.split(' / ')[1].strip()
            return self._convert_to_bytes(write_part)
        except:
            return 0
    
    def _convert_to_bytes(self, size_str: str) -> int:
        """Convert size string to bytes"""
        try:
            size_str = size_str.strip()
            if size_str.endswith('B'):
                size_str = size_str[:-1]
            
            multipliers = {
                'K': 1024, 'Ki': 1024,
                'M': 1024**2, 'Mi': 1024**2,
                'G': 1024**3, 'Gi': 1024**3,
                'T': 1024**4, 'Ti': 1024**4
            }
            
            for suffix, multiplier in multipliers.items():
                if size_str.endswith(suffix):
                    number = float(size_str[:-len(suffix)])
                    return int(number * multiplier)
            
            return int(float(size_str))
        except:
            return 0
    
    def save_metrics(self, containers: List[Dict]):
        """Save metrics to configured output"""
        if self.output_type == "csv":
            self._save_to_csv(containers)
        elif self.output_type == "influxdb":
            self._save_to_influxdb(containers)
    
    def _save_to_csv(self, containers: List[Dict]):
        """Save metrics to CSV"""
        self.csv_data.extend(containers)
        
        if self.output_file:
            df = pd.DataFrame(containers)
            if os.path.exists(self.output_file):
                df.to_csv(self.output_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.output_file, index=False)
    
    def _save_to_influxdb(self, containers: List[Dict]):
        """Save metrics to InfluxDB"""
        if not self.write_api:
            return False
        
        try:
            points = []
            timestamp = datetime.utcnow()
            
            for container in containers:
                point = Point("container_metrics") \
                    .tag("service_name", container['service_name']) \
                    .tag("container_name", container['container_name']) \
                    .tag("container_id", container['container_id']) \
                    .field("cpu_percent", container['cpu_percent']) \
                    .field("memory_usage_bytes", container['memory_usage_bytes']) \
                    .field("memory_limit_bytes", container['memory_limit_bytes']) \
                    .field("memory_usage_percent", container['memory_usage_percent']) \
                    .field("network_rx_bytes", container['network_rx_bytes']) \
                    .field("network_tx_bytes", container['network_tx_bytes']) \
                    .field("block_read_bytes", container['block_read_bytes']) \
                    .field("block_write_bytes", container['block_write_bytes']) \
                    .field("pids", container['pids']) \
                    .time(timestamp, WritePrecision.NS)
                
                points.append(point)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            return True
            
        except Exception as e:
            print(f"❌ Error writing to InfluxDB: {e}")
            return False
    
    def collect_continuously(self, duration_minutes=5, interval_seconds=5):
        """Collect metrics continuously"""
        print(f"\n📊 Starting continuous collection...")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print(f"🔄 Interval: {interval_seconds} seconds")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        collection_count = 0
        
        try:
            while time.time() < end_time:
                containers = self.get_container_metrics()
                
                if containers:
                    self.save_metrics(containers)
                    collection_count += 1
                    
                    elapsed = time.time() - start_time
                    remaining = end_time - time.time()
                    progress = (elapsed / (duration_minutes * 60)) * 100
                    
                    print(f"📊 Progress: {progress:.1f}% | Collections: {collection_count} | "
                          f"Containers: {len(containers)} | Remaining: {remaining/60:.1f}m", end='\r')
                else:
                    print(f"\n⚠️  No containers found at {datetime.now()}")
                
                time.sleep(interval_seconds)
            
            print(f"\n✅ Collection completed!")
            print(f"📊 Total collections: {collection_count}")
            
            if self.output_type == "csv" and self.csv_data:
                print(f"📄 CSV records: {len(self.csv_data)}")
            elif self.output_type == "influxdb":
                print(f"🗄️  Data stored in InfluxDB bucket: {self.bucket}")
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Collection interrupted by user")
            print(f"📊 Collections completed: {collection_count}")
            return True
        except Exception as e:
            print(f"\n❌ Collection failed: {e}")
            return False
        finally:
            if self.influx_client:
                self.influx_client.close()

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="PHCA Metrics Collector")
    parser.add_argument("--output", choices=["csv", "influxdb"], default="influxdb",
                       help="Output type (default: influxdb)")
    parser.add_argument("--file", help="CSV output file (for CSV output)")
    parser.add_argument("--duration", type=int, default=5,
                       help="Collection duration in minutes (default: 5)")
    parser.add_argument("--interval", type=int, default=5,
                       help="Collection interval in seconds (default: 5)")
    
    # InfluxDB options
    parser.add_argument("--influx-url", default="http://localhost:8086",
                       help="InfluxDB URL (default: http://localhost:8086)")
    parser.add_argument("--influx-token", default="phca-token-12345",
                       help="InfluxDB token")
    parser.add_argument("--influx-org", default="phca",
                       help="InfluxDB organization")
    parser.add_argument("--influx-bucket", default="microservices",
                       help="InfluxDB bucket")
    
    args = parser.parse_args()
    
    # Setup output configuration
    if args.output == "csv":
        output_file = args.file or f"phca_metrics_{int(time.time())}.csv"
        collector = PHCAMetricsCollector(
            output_type="csv",
            output_file=output_file
        )
    else:
        influx_config = {
            'url': args.influx_url,
            'token': args.influx_token,
            'org': args.influx_org,
            'bucket': args.influx_bucket
        }
        collector = PHCAMetricsCollector(
            output_type="influxdb",
            influx_config=influx_config
        )
    
    # Start collection
    collector.collect_continuously(
        duration_minutes=args.duration,
        interval_seconds=args.interval
    )

if __name__ == "__main__":
    main()