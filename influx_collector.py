#!/usr/bin/env python3
"""
PHCA InfluxDB Metrics Collector
Collects Docker metrics and stores in InfluxDB time-series database
"""

import subprocess
import time
import os
from datetime import datetime
from typing import Dict, List
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class PHCAInfluxCollector:
    def __init__(self, 
                 influx_url="http://localhost:8086",
                 token="phca-token-12345",
                 org="phca",
                 bucket="microservices"):
        
        self.influx_url = influx_url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        # Sock Shop services
        self.target_services = [
            'front-end', 'catalogue', 'catalogue-db', 'carts', 'carts-db',
            'orders', 'orders-db', 'shipping', 'queue-master', 'rabbitmq',
            'payment', 'user', 'user-db', 'edge-router'
        ]
        
        # Initialize InfluxDB client
        self.client = None
        self.write_api = None
        
        print(f"🎯 PHCA InfluxDB Collector")
        print(f"📊 Target services: {len(self.target_services)}")
        print(f"🗄️  Database: {influx_url}")
    
    def connect_influxdb(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(url=self.influx_url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                print("✅ InfluxDB connection successful")
                return True
            else:
                print(f"❌ InfluxDB health check failed: {health.status}")
                return False
                
        except Exception as e:
            print(f"❌ InfluxDB connection failed: {e}")
            return False
    
    def get_docker_containers(self):
        """Get running Docker containers using docker stats"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                '{{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}'
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
                            pids = parts[6] if len(parts) > 6 else "0"
                            
                            service_name = self._extract_service_name(name)
                            if service_name in self.target_services:
                                containers.append({
                                    'container_id': container_id,
                                    'name': name,
                                    'service_name': service_name,
                                    'cpu_percent': self._parse_cpu_percent(cpu_percent),
                                    'memory_usage_raw': memory_usage,
                                    'memory_usage_bytes': self._parse_memory_bytes(memory_usage),
                                    'memory_limit_bytes': self._parse_memory_limit(memory_usage),
                                    'network_io_raw': network_io,
                                    'network_rx_bytes': self._parse_network_rx(network_io),
                                    'network_tx_bytes': self._parse_network_tx(network_io),
                                    'block_io_raw': block_io,
                                    'block_read_bytes': self._parse_block_read(block_io),
                                    'block_write_bytes': self._parse_block_write(block_io),
                                    'pids': int(pids) if pids.isdigit() else 0
                                })
                
                return containers
            else:
                print(f"❌ Docker stats error: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting Docker containers: {e}")
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
            # Format: "367.8MiB / 7.617GiB"
            usage_part = mem_str.split(' / ')[0].strip()
            return self._convert_to_bytes(usage_part)
        except:
            return 0
    
    def _parse_memory_limit(self, mem_str: str) -> int:
        """Parse memory limit in bytes"""
        try:
            # Format: "367.8MiB / 7.617GiB"
            limit_part = mem_str.split(' / ')[1].strip()
            return self._convert_to_bytes(limit_part)
        except:
            return 0
    
    def _parse_network_rx(self, net_str: str) -> int:
        """Parse network received bytes"""
        try:
            # Format: "20.3MB / 142MB"
            rx_part = net_str.split(' / ')[0].strip()
            return self._convert_to_bytes(rx_part)
        except:
            return 0
    
    def _parse_network_tx(self, net_str: str) -> int:
        """Parse network transmitted bytes"""
        try:
            # Format: "20.3MB / 142MB"
            tx_part = net_str.split(' / ')[1].strip()
            return self._convert_to_bytes(tx_part)
        except:
            return 0
    
    def _parse_block_read(self, block_str: str) -> int:
        """Parse block read bytes"""
        try:
            # Format: "24.3MB / 0B"
            read_part = block_str.split(' / ')[0].strip()
            return self._convert_to_bytes(read_part)
        except:
            return 0
    
    def _parse_block_write(self, block_str: str) -> int:
        """Parse block write bytes"""
        try:
            # Format: "24.3MB / 0B"
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
            
            # No suffix, assume bytes
            return int(float(size_str))
            
        except:
            return 0
    
    def write_metrics_to_influx(self, containers: List[Dict]):
        """Write container metrics to InfluxDB"""
        if not self.write_api:
            print("❌ InfluxDB not connected")
            return False
        
        try:
            points = []
            timestamp = datetime.utcnow()
            
            for container in containers:
                # Create a point for each container
                point = Point("container_metrics") \
                    .tag("service_name", container['service_name']) \
                    .tag("container_name", container['name']) \
                    .tag("container_id", container['container_id']) \
                    .field("cpu_percent", container['cpu_percent']) \
                    .field("memory_usage_bytes", container['memory_usage_bytes']) \
                    .field("memory_limit_bytes", container['memory_limit_bytes']) \
                    .field("memory_usage_percent", 
                           (container['memory_usage_bytes'] / container['memory_limit_bytes'] * 100) 
                           if container['memory_limit_bytes'] > 0 else 0) \
                    .field("network_rx_bytes", container['network_rx_bytes']) \
                    .field("network_tx_bytes", container['network_tx_bytes']) \
                    .field("block_read_bytes", container['block_read_bytes']) \
                    .field("block_write_bytes", container['block_write_bytes']) \
                    .field("pids", container['pids']) \
                    .time(timestamp, WritePrecision.NS)
                
                points.append(point)
            
            # Write all points
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            return True
            
        except Exception as e:
            print(f"❌ Error writing to InfluxDB: {e}")
            return False
    
    def collect_metrics_continuously(self, duration_minutes: int = 60, interval_seconds: int = 5):
        """Collect metrics continuously and store in InfluxDB"""
        
        if not self.connect_influxdb():
            print("❌ Cannot connect to InfluxDB")
            return False
        
        print(f"📊 Starting continuous collection...")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print(f"🔄 Interval: {interval_seconds} seconds")
        print(f"🗄️  Storing in: {self.bucket} bucket")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        collection_count = 0
        
        try:
            while time.time() < end_time:
                # Get container metrics
                containers = self.get_docker_containers()
                
                if containers:
                    # Write to InfluxDB
                    if self.write_metrics_to_influx(containers):
                        collection_count += 1
                        
                        # Progress indicator
                        elapsed = time.time() - start_time
                        remaining = end_time - time.time()
                        progress = (elapsed / (duration_minutes * 60)) * 100
                        
                        print(f"📊 Progress: {progress:.1f}% | Collections: {collection_count} | "
                              f"Containers: {len(containers)} | Remaining: {remaining/60:.1f}m", end='\r')
                    else:
                        print(f"\n❌ Failed to write metrics at {datetime.now()}")
                else:
                    print(f"\n⚠️  No containers found at {datetime.now()}")
                
                time.sleep(interval_seconds)
            
            print(f"\n✅ Collection completed!")
            print(f"📊 Total collections: {collection_count}")
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
            if self.client:
                self.client.close()
    
    def query_metrics(self, service_name: str = None, last_minutes: int = 60):
        """Query metrics from InfluxDB"""
        if not self.connect_influxdb():
            return None
        
        try:
            query_api = self.client.query_api()
            
            # Build Flux query
            time_range = f"-{last_minutes}m"
            
            if service_name:
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {time_range})
                  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
                  |> filter(fn: (r) => r["service_name"] == "{service_name}")
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            else:
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {time_range})
                  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            
            result = query_api.query(org=self.org, query=query)
            
            # Convert to list of dictionaries
            data = []
            for table in result:
                for record in table.records:
                    data.append(record.values)
            
            return data
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return None
        finally:
            if self.client:
                self.client.close()

def main():
    """Main function"""
    collector = PHCAInfluxCollector()
    
    print("\n🎯 PHCA InfluxDB Collector")
    print("=" * 50)
    
    # Check if containers are available
    containers = collector.get_docker_containers()
    if containers:
        print(f"📦 Found {len(containers)} Sock Shop containers:")
        for container in containers[:3]:
            print(f"  • {container['service_name']}: CPU={container['cpu_percent']:.2f}% "
                  f"Memory={container['memory_usage_bytes']/(1024**2):.1f}MB")
        if len(containers) > 3:
            print(f"  ... and {len(containers)-3} more")
    else:
        print("❌ No Sock Shop containers found!")
        print("💡 Start Sock Shop first:")
        print("   cd microservices-demo")
        print("   docker-compose up -d")
        return
    
    print(f"\n💡 Make sure InfluxDB is running:")
    print(f"   cd influx-stack")
    print(f"   docker-compose up -d")
    print(f"   # Wait 30 seconds for startup")
    
    # Ask user what to do
    print(f"\nOptions:")
    print(f"1. Test InfluxDB connection")
    print(f"2. Collect metrics for 5 minutes")
    print(f"3. Query recent metrics")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        if collector.connect_influxdb():
            print("✅ InfluxDB connection test successful!")
        else:
            print("❌ InfluxDB connection test failed!")
    
    elif choice == "2":
        collector.collect_metrics_continuously(duration_minutes=5)
    
    elif choice == "3":
        data = collector.query_metrics(last_minutes=60)
        if data:
            print(f"📊 Found {len(data)} records in last 60 minutes")
            if data:
                print("Sample record:")
                for key, value in list(data[0].items())[:10]:
                    print(f"  {key}: {value}")
        else:
            print("❌ No data found or query failed")

if __name__ == "__main__":
    main()