#!/usr/bin/env python3
"""
Docker Metrics Collector for PHCA Research
Collects metrics from Docker containers and saves to CSV or InfluxDB
Uses HTTP API for InfluxDB (compatible with Docker Desktop)
"""

import subprocess
import time
import csv
import argparse
from datetime import datetime
import os
import requests


class DockerMetricsCollector:
    def __init__(self, output_type="csv", output_file=None):
        self.output_type = output_type
        self.output_file = output_file
        
        # InfluxDB settings (HTTP API)
        self.influx_url = "http://localhost:8086"
        self.token = "phca-token-12345"
        self.org = "phca"
        self.bucket = "microservices"
        
        if output_type == "influxdb":
            self.setup_influxdb()
        elif output_type == "csv":
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.output_file = f"results/docker_metrics_{timestamp}.csv"
            os.makedirs("results", exist_ok=True)
            self.init_csv()
    
    def setup_influxdb(self):
        """Test InfluxDB connection using HTTP API"""
        print("🔗 Connecting to InfluxDB...")
        try:
            response = requests.get(f'{self.influx_url}/health')
            if response.status_code == 200:
                print("✅ Connected to InfluxDB")
            else:
                print(f"⚠️  InfluxDB health check returned: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect to InfluxDB: {e}")
            raise
    
    def init_csv(self):
        """Initialize CSV file with headers"""
        with open(self.output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'container_id', 'container_name', 'service_name',
                'cpu_percent', 'memory_usage_bytes', 'memory_limit_bytes', 'memory_percent',
                'network_rx_bytes', 'network_tx_bytes', 
                'block_read_bytes', 'block_write_bytes', 'pids'
            ])
        print(f"📁 CSV file created: {self.output_file}")
    
    def get_docker_stats(self):
        """Get Docker stats for all running containers"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format',
                '{{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"❌ Docker stats error: {result.stderr}")
                return []
            
            metrics = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 8:
                        container_id = parts[0]
                        container_name = parts[1]
                        
                        # Extract service name
                        service_name = self._extract_service_name(container_name)
                        
                        # Parse metrics
                        cpu_percent = self._parse_percent(parts[2])
                        memory_usage, memory_limit = self._parse_memory(parts[3])
                        memory_percent = self._parse_percent(parts[4])
                        net_rx, net_tx = self._parse_network(parts[5])
                        block_read, block_write = self._parse_block_io(parts[6])
                        pids = int(parts[7]) if parts[7].isdigit() else 0
                        
                        metrics.append({
                            'container_id': container_id,
                            'container_name': container_name,
                            'service_name': service_name,
                            'cpu_percent': cpu_percent,
                            'memory_usage_bytes': memory_usage,
                            'memory_limit_bytes': memory_limit,
                            'memory_percent': memory_percent,
                            'network_rx_bytes': net_rx,
                            'network_tx_bytes': net_tx,
                            'block_read_bytes': block_read,
                            'block_write_bytes': block_write,
                            'pids': pids
                        })
            
            return metrics
            
        except Exception as e:
            print(f"❌ Error collecting metrics: {e}")
            return []
    
    def _extract_service_name(self, container_name):
        """Extract service name from container name"""
        # Remove common prefixes
        name = container_name.lower()
        for prefix in ['docker-compose-', 'microservices-demo-', 'sock-shop-']:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Remove trailing numbers
        for suffix in ['-1', '-2', '-3', '-db-1', '-db-2']:
            if name.endswith(suffix):
                name = name[:name.rfind(suffix)]
        
        return name
    
    def _parse_percent(self, percent_str):
        """Parse percentage string"""
        try:
            return float(percent_str.replace('%', ''))
        except:
            return 0.0
    
    def _parse_memory(self, memory_str):
        """Parse memory usage string like '100MiB / 2GiB'"""
        try:
            parts = memory_str.split(' / ')
            usage = self._convert_to_bytes(parts[0])
            limit = self._convert_to_bytes(parts[1])
            return usage, limit
        except:
            return 0, 0
    
    def _convert_to_bytes(self, size_str):
        """Convert size string to bytes"""
        size_str = size_str.strip()
        try:
            if 'GiB' in size_str or 'GB' in size_str:
                return int(float(size_str.replace('GiB', '').replace('GB', '')) * 1024 * 1024 * 1024)
            elif 'MiB' in size_str or 'MB' in size_str:
                return int(float(size_str.replace('MiB', '').replace('MB', '')) * 1024 * 1024)
            elif 'KiB' in size_str or 'KB' in size_str or 'kB' in size_str:
                return int(float(size_str.replace('KiB', '').replace('KB', '').replace('kB', '')) * 1024)
            elif 'B' in size_str:
                return int(float(size_str.replace('B', '')))
        except:
            pass
        return 0
    
    def _parse_network(self, network_str):
        """Parse network I/O string like '1.2kB / 800B'"""
        try:
            parts = network_str.split(' / ')
            rx = self._convert_to_bytes(parts[0])
            tx = self._convert_to_bytes(parts[1])
            return rx, tx
        except:
            return 0, 0
    
    def _parse_block_io(self, block_str):
        """Parse block I/O string like '1.2MB / 0B'"""
        try:
            parts = block_str.split(' / ')
            read = self._convert_to_bytes(parts[0])
            write = self._convert_to_bytes(parts[1])
            return read, write
        except:
            return 0, 0
    
    def save_to_csv(self, metrics, timestamp):
        """Save metrics to CSV file"""
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for m in metrics:
                writer.writerow([
                    timestamp, m['container_id'], m['container_name'], m['service_name'],
                    m['cpu_percent'], m['memory_usage_bytes'], m['memory_limit_bytes'], m['memory_percent'],
                    m['network_rx_bytes'], m['network_tx_bytes'],
                    m['block_read_bytes'], m['block_write_bytes'], m['pids']
                ])
    
    def save_to_influxdb(self, metrics, timestamp):
        """Save metrics to InfluxDB using HTTP API (line protocol)"""
        try:
            # Convert to line protocol
            lines = []
            ts_ns = int(timestamp.timestamp() * 1000000000)
            
            for m in metrics:
                # Escape special characters in tags
                container_id = m['container_id'].replace(',', '\\,').replace(' ', '\\ ').replace('=', '\\=')
                container_name = m['container_name'].replace(',', '\\,').replace(' ', '\\ ').replace('=', '\\=')
                service_name = m['service_name'].replace(',', '\\,').replace(' ', '\\ ').replace('=', '\\=')
                
                tags = f"container_id={container_id},container_name={container_name},service_name={service_name}"
                fields = f"cpu_percent={m['cpu_percent']},memory_usage_bytes={m['memory_usage_bytes']}i,memory_limit_bytes={m['memory_limit_bytes']}i,memory_usage_percent={m['memory_percent']},network_rx_bytes={m['network_rx_bytes']}i,network_tx_bytes={m['network_tx_bytes']}i,block_read_bytes={m['block_read_bytes']}i,block_write_bytes={m['block_write_bytes']}i,pids={m['pids']}i"
                line = f"container_metrics,{tags} {fields} {ts_ns}"
                lines.append(line)
            
            data = '\n'.join(lines)
            
            # Write using HTTP API
            response = requests.post(
                f'{self.influx_url}/api/v2/write?org={self.org}&bucket={self.bucket}',
                headers={'Authorization': f'Token {self.token}'},
                data=data
            )
            
            if response.status_code == 204:
                return True
            else:
                print(f"❌ InfluxDB write failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error writing to InfluxDB: {e}")
            return False
    
    def collect_once(self):
        """Collect metrics once"""
        timestamp = datetime.now()
        metrics = self.get_docker_stats()
        
        if not metrics:
            print("⚠️  No containers found")
            return False
        
        # Save metrics
        success = False
        if self.output_type == "csv":
            self.save_to_csv(metrics, timestamp.isoformat())
            success = True
        elif self.output_type == "influxdb":
            success = self.save_to_influxdb(metrics, timestamp)
            if success:
                print(f"✅ Wrote {len(metrics)} points to InfluxDB at {timestamp.strftime('%H:%M:%S')}")
        
        # Print summary
        print(f"📊 Collected metrics from {len(metrics)} containers")
        
        # Show top CPU users
        metrics.sort(key=lambda x: x['cpu_percent'], reverse=True)
        print("   Top CPU users:")
        for m in metrics[:5]:
            print(f"      {m['service_name']:15} - {m['cpu_percent']:5.2f}% CPU, {m['memory_usage_bytes']/(1024*1024):6.1f}MB RAM")
        
        return success
    
    def collect_continuous(self, interval=5, duration=300):
        """Collect metrics continuously"""
        print(f"🚀 Starting continuous collection:")
        print(f"   Interval: {interval} seconds")
        print(f"   Duration: {duration} seconds")
        if self.output_type == "csv":
            print(f"   Output: {self.output_file}")
        else:
            print(f"   Output: InfluxDB ({self.bucket} bucket)")
        print(f"   Press Ctrl+C to stop early")
        print()
        
        start_time = time.time()
        collection_count = 0
        success_count = 0
        
        try:
            while time.time() - start_time < duration:
                if self.collect_once():
                    success_count += 1
                collection_count += 1
                print()
                
                remaining = duration - (time.time() - start_time)
                if remaining > interval:
                    time.sleep(interval)
                else:
                    break
        
        except KeyboardInterrupt:
            print("\n⚠️  Collection stopped by user")
        
        print(f"\n✅ Collection completed!")
        print(f"   Collections: {collection_count}")
        if self.output_type == "influxdb":
            print(f"   Successful writes: {success_count}")
        print(f"   Duration: {time.time() - start_time:.1f} seconds")
        if self.output_type == "csv":
            print(f"   File: {self.output_file}")
    
    def close(self):
        """Close connections (no-op for HTTP API)"""
        pass


def main():
    parser = argparse.ArgumentParser(description="Collect Docker container metrics")
    parser.add_argument("--output", choices=["csv", "influxdb"], default="csv",
                        help="Output type: csv or influxdb (default: csv)")
    parser.add_argument("--file", type=str, help="Output CSV file (default: auto-generated)")
    parser.add_argument("--interval", type=int, default=5, help="Collection interval in seconds (default: 5)")
    parser.add_argument("--duration", type=int, default=300, help="Total duration in seconds (default: 300)")
    parser.add_argument("--once", action="store_true", help="Collect once and exit")
    
    args = parser.parse_args()
    
    # Create collector
    try:
        collector = DockerMetricsCollector(output_type=args.output, output_file=args.file)
    except Exception as e:
        print(f"❌ Failed to initialize collector: {e}")
        return
    
    try:
        if args.once:
            collector.collect_once()
        else:
            collector.collect_continuous(args.interval, args.duration)
    finally:
        collector.close()


if __name__ == "__main__":
    main()
