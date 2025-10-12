#!/usr/bin/env python3
"""
JSON Metrics Collector for ML Processing
Collects raw metrics from Docker containers and exports to JSON format
"""

import subprocess
import json
import sys
import time
from datetime import datetime
import argparse
import signal

class MetricsCollector:
    def __init__(self, output_file=None, interval=5, duration=None):
        self.output_file = output_file
        self.interval = interval
        self.duration = duration
        self.metrics_data = []
        self.start_time = time.time()
        self.running = True
        
        # Service categories
        self.microservices = [
            'cart', 'checkout', 'frontend', 'product-catalog', 'recommendation',
            'payment', 'shipping', 'currency', 'email', 'ad', 'accounting', 'fraud-detection'
        ]
        self.infrastructure = ['prometheus', 'otel-collector', 'grafana', 'jaeger']
        
    def parse_size_to_bytes(self, size_str):
        """Convert size string to bytes"""
        size_str = size_str.strip()
        
        if 'kB' in size_str or 'KB' in size_str:
            return float(size_str.replace('kB', '').replace('KB', '').strip()) * 1024
        elif 'MB' in size_str or 'MiB' in size_str:
            return float(size_str.replace('MB', '').replace('MiB', '').strip()) * 1024 * 1024
        elif 'GB' in size_str or 'GiB' in size_str:
            return float(size_str.replace('GB', '').replace('GiB', '').strip()) * 1024 * 1024 * 1024
        elif 'B' in size_str:
            return float(size_str.replace('B', '').strip())
        else:
            return 0.0
    
    def parse_docker_stats(self):
        """Get Docker stats for all containers"""
        try:
            cmd = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            stats = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    name = data['Name']
                    
                    # Parse CPU percentage
                    cpu_str = data['CPUPerc'].replace('%', '')
                    cpu = float(cpu_str) if cpu_str else 0.0
                    
                    # Parse memory usage
                    mem_usage_str = data['MemUsage'].split('/')[0].strip()
                    mem_limit_str = data['MemUsage'].split('/')[1].strip() if '/' in data['MemUsage'] else '0B'
                    
                    mem_usage_bytes = self.parse_size_to_bytes(mem_usage_str)
                    mem_limit_bytes = self.parse_size_to_bytes(mem_limit_str)
                    
                    # Parse memory percentage
                    mem_perc_str = data['MemPerc'].replace('%', '')
                    mem_perc = float(mem_perc_str) if mem_perc_str else 0.0
                    
                    # Parse network I/O
                    net_io = data['NetIO']
                    net_parts = net_io.split('/')
                    net_in_str = net_parts[0].strip() if len(net_parts) > 0 else '0B'
                    net_out_str = net_parts[1].strip() if len(net_parts) > 1 else '0B'
                    
                    net_in_bytes = self.parse_size_to_bytes(net_in_str)
                    net_out_bytes = self.parse_size_to_bytes(net_out_str)
                    
                    # Parse block I/O
                    block_io = data.get('BlockIO', '0B / 0B')
                    block_parts = block_io.split('/')
                    block_read_str = block_parts[0].strip() if len(block_parts) > 0 else '0B'
                    block_write_str = block_parts[1].strip() if len(block_parts) > 1 else '0B'
                    
                    block_read_bytes = self.parse_size_to_bytes(block_read_str)
                    block_write_bytes = self.parse_size_to_bytes(block_write_str)
                    
                    # Parse PIDs
                    pids_str = data.get('PIDs', '0')
                    pids = int(pids_str) if pids_str.isdigit() else 0
                    
                    stats[name] = {
                        'container_id': data.get('Container', ''),
                        'cpu_percent': cpu,
                        'memory': {
                            'usage_bytes': mem_usage_bytes,
                            'limit_bytes': mem_limit_bytes,
                            'usage_mb': mem_usage_bytes / (1024 * 1024),
                            'limit_mb': mem_limit_bytes / (1024 * 1024),
                            'percent': mem_perc
                        },
                        'network': {
                            'rx_bytes': net_in_bytes,
                            'tx_bytes': net_out_bytes,
                            'rx_mb': net_in_bytes / (1024 * 1024),
                            'tx_mb': net_out_bytes / (1024 * 1024)
                        },
                        'block_io': {
                            'read_bytes': block_read_bytes,
                            'write_bytes': block_write_bytes,
                            'read_mb': block_read_bytes / (1024 * 1024),
                            'write_mb': block_write_bytes / (1024 * 1024)
                        },
                        'pids': pids
                    }
            
            return stats
        except Exception as e:
            print(f"Error getting Docker stats: {e}", file=sys.stderr)
            return {}
    
    def get_locust_stats(self):
        """Get Locust statistics"""
        try:
            # Try multiple common Locust ports
            ports = [32852, 32851, 32850, 32823, 32822, 8089]
            
            for port in ports:
                try:
                    result = subprocess.run(
                        ["curl", "-s", f"http://localhost:{port}/stats/requests"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        data = json.loads(result.stdout)
                        
                        # Get total stats
                        total_rps = data.get('total_rps', 0) or 0
                        fail_ratio = data.get('fail_ratio', 0) or 0
                        
                        # Get percentiles
                        percentiles = data.get('current_response_time_percentiles', {})
                        
                        # Get user count
                        user_count = data.get('user_count', 0) or 0
                        
                        # Get stats per endpoint
                        stats_list = data.get('stats', [])
                        endpoints = []
                        for stat in stats_list:
                            if stat.get('name') != 'Aggregated':
                                endpoints.append({
                                    'name': stat.get('name', ''),
                                    'method': stat.get('method', ''),
                                    'num_requests': stat.get('num_requests', 0),
                                    'num_failures': stat.get('num_failures', 0),
                                    'avg_response_time': stat.get('avg_response_time', 0),
                                    'min_response_time': stat.get('min_response_time', 0),
                                    'max_response_time': stat.get('max_response_time', 0),
                                    'current_rps': stat.get('current_rps', 0),
                                    'current_fail_per_sec': stat.get('current_fail_per_sec', 0),
                                    'median_response_time': stat.get('median_response_time', 0),
                                    'ninetieth_response_time': stat.get('ninetieth_response_time', 0),
                                    'ninety_fifth_response_time': stat.get('ninety_fifth_response_time', 0),
                                    'ninety_ninth_response_time': stat.get('ninety_ninth_response_time', 0)
                                })
                        
                        return {
                            'available': True,
                            'port': port,
                            'total_rps': float(total_rps),
                            'fail_ratio': float(fail_ratio),
                            'user_count': int(user_count),
                            'response_time_percentiles': {
                                'p50': float(percentiles.get('response_time_percentile_0.5', 0) or 0),
                                'p75': float(percentiles.get('response_time_percentile_0.75', 0) or 0),
                                'p90': float(percentiles.get('response_time_percentile_0.9', 0) or 0),
                                'p95': float(percentiles.get('response_time_percentile_0.95', 0) or 0),
                                'p99': float(percentiles.get('response_time_percentile_0.99', 0) or 0)
                            },
                            'endpoints': endpoints,
                            'total_stats': data.get('total_stats', {})
                        }
                except:
                    continue
        except:
            pass
        
        return {'available': False}
    
    def collect_snapshot(self):
        """Collect a single snapshot of metrics"""
        timestamp = datetime.now().isoformat()
        elapsed = time.time() - self.start_time
        
        docker_stats = self.parse_docker_stats()
        locust_stats = self.get_locust_stats()
        
        # Organize by service type
        microservices_data = {}
        infrastructure_data = {}
        other_services = {}
        
        for service_name, stats in docker_stats.items():
            if service_name in self.microservices:
                microservices_data[service_name] = stats
            elif service_name in self.infrastructure:
                infrastructure_data[service_name] = stats
            else:
                other_services[service_name] = stats
        
        snapshot = {
            'timestamp': timestamp,
            'elapsed_seconds': elapsed,
            'collection_interval': self.interval,
            'load_generator': locust_stats,
            'services': {
                'microservices': microservices_data,
                'infrastructure': infrastructure_data,
                'other': other_services
            },
            'summary': {
                'total_services': len(docker_stats),
                'microservices_count': len(microservices_data),
                'infrastructure_count': len(infrastructure_data),
                'total_cpu_percent': sum(s['cpu_percent'] for s in docker_stats.values()),
                'total_memory_mb': sum(s['memory']['usage_mb'] for s in docker_stats.values()),
                'total_network_rx_mb': sum(s['network']['rx_mb'] for s in docker_stats.values()),
                'total_network_tx_mb': sum(s['network']['tx_mb'] for s in docker_stats.values())
            }
        }
        
        return snapshot
    
    def print_snapshot_summary(self, snapshot):
        """Print a human-readable summary of the snapshot"""
        print(f"\n[{snapshot['timestamp']}] Snapshot collected (elapsed: {snapshot['elapsed_seconds']:.1f}s)")
        
        if snapshot['load_generator']['available']:
            lg = snapshot['load_generator']
            print(f"  Load: {lg['total_rps']:.1f} RPS, {lg['user_count']} users, "
                  f"P95: {lg['response_time_percentiles']['p95']:.0f}ms, "
                  f"Fail: {lg['fail_ratio']*100:.2f}%")
        else:
            print(f"  Load: Not available")
        
        summary = snapshot['summary']
        print(f"  Services: {summary['microservices_count']} microservices, "
              f"{summary['infrastructure_count']} infrastructure")
        print(f"  Resources: CPU {summary['total_cpu_percent']:.1f}%, "
              f"Memory {summary['total_memory_mb']:.1f}MB, "
              f"Network RX/TX {summary['total_network_rx_mb']:.1f}/{summary['total_network_tx_mb']:.1f}MB")
    
    def save_to_file(self):
        """Save collected metrics to JSON file"""
        if not self.output_file:
            return
        
        output_data = {
            'metadata': {
                'collection_start': datetime.fromtimestamp(self.start_time).isoformat(),
                'collection_end': datetime.now().isoformat(),
                'total_duration_seconds': time.time() - self.start_time,
                'collection_interval_seconds': self.interval,
                'total_snapshots': len(self.metrics_data),
                'services_monitored': {
                    'microservices': self.microservices,
                    'infrastructure': self.infrastructure
                }
            },
            'snapshots': self.metrics_data
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✓ Saved {len(self.metrics_data)} snapshots to {self.output_file}")
        print(f"  File size: {len(json.dumps(output_data)) / 1024:.1f} KB")
    
    def run(self):
        """Run the metrics collection"""
        print("=" * 80)
        print("JSON METRICS COLLECTOR FOR ML")
        print("=" * 80)
        print(f"Collection interval: {self.interval}s")
        if self.duration:
            print(f"Duration: {self.duration}s ({self.duration // 60} minutes)")
        else:
            print("Duration: Continuous (Ctrl+C to stop)")
        if self.output_file:
            print(f"Output file: {self.output_file}")
        else:
            print("Output: stdout only")
        print("=" * 80)
        
        # Setup signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\n\nReceived interrupt signal, stopping collection...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            snapshot_count = 0
            while self.running:
                # Collect snapshot
                snapshot = self.collect_snapshot()
                self.metrics_data.append(snapshot)
                snapshot_count += 1
                
                # Print summary
                self.print_snapshot_summary(snapshot)
                
                # Check duration
                if self.duration and (time.time() - self.start_time) >= self.duration:
                    print(f"\n✓ Reached target duration of {self.duration}s")
                    break
                
                # Wait for next interval
                time.sleep(self.interval)
            
            # Save to file
            if self.output_file:
                self.save_to_file()
            else:
                # Print to stdout
                output_data = {
                    'metadata': {
                        'collection_start': datetime.fromtimestamp(self.start_time).isoformat(),
                        'collection_end': datetime.now().isoformat(),
                        'total_duration_seconds': time.time() - self.start_time,
                        'collection_interval_seconds': self.interval,
                        'total_snapshots': len(self.metrics_data)
                    },
                    'snapshots': self.metrics_data
                }
                print("\n" + "=" * 80)
                print("JSON OUTPUT")
                print("=" * 80)
                print(json.dumps(output_data, indent=2))
        
        except Exception as e:
            print(f"\nError during collection: {e}", file=sys.stderr)
            if self.output_file and self.metrics_data:
                print("Attempting to save partial data...")
                self.save_to_file()

def main():
    parser = argparse.ArgumentParser(
        description='Collect Docker metrics in JSON format for ML processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect for 5 minutes, save to file
  ./collect_metrics_json.py -o metrics.json -d 300
  
  # Collect continuously with 10s interval
  ./collect_metrics_json.py -i 10 -o metrics.json
  
  # Collect for 1 hour during load test
  ./collect_metrics_json.py -o load_test_metrics.json -d 3600 -i 5
  
  # Print to stdout (pipe to jq for pretty printing)
  ./collect_metrics_json.py -d 60 | jq .
        """
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file path (if not specified, prints to stdout)',
        default=None
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=5,
        help='Collection interval in seconds (default: 5)'
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=None,
        help='Total duration in seconds (default: continuous until Ctrl+C)'
    )
    
    args = parser.parse_args()
    
    collector = MetricsCollector(
        output_file=args.output,
        interval=args.interval,
        duration=args.duration
    )
    
    collector.run()

if __name__ == "__main__":
    main()
