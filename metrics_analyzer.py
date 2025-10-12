#!/usr/bin/env python3
"""
Metrics Analysis Tool
Analyzes collected JSON metrics for ML preprocessing and insights
"""

import json
import sys
import argparse
from datetime import datetime
import statistics

class MetricsAnalyzer:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = None
        
    def load_data(self):
        """Load JSON data from file"""
        try:
            with open(self.json_file, 'r') as f:
                self.data = json.load(f)
            print(f"✓ Loaded {len(self.data['snapshots'])} snapshots from {self.json_file}")
            return True
        except Exception as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            return False
    
    def print_summary(self):
        """Print summary statistics"""
        if not self.data:
            return
        
        metadata = self.data['metadata']
        snapshots = self.data['snapshots']
        
        print("\n" + "=" * 80)
        print("METRICS SUMMARY")
        print("=" * 80)
        
        print(f"\nCollection Period:")
        print(f"  Start: {metadata['collection_start']}")
        print(f"  End: {metadata['collection_end']}")
        print(f"  Duration: {metadata['total_duration_seconds']:.1f}s ({metadata['total_duration_seconds']/60:.1f} min)")
        print(f"  Interval: {metadata['collection_interval_seconds']}s")
        print(f"  Snapshots: {metadata['total_snapshots']}")
        
        # Analyze load generator data
        load_available = [s['load_generator']['available'] for s in snapshots]
        if any(load_available):
            load_snapshots = [s['load_generator'] for s in snapshots if s['load_generator']['available']]
            
            rps_values = [s['total_rps'] for s in load_snapshots]
            users = [s['user_count'] for s in load_snapshots]
            p95_values = [s['response_time_percentiles']['p95'] for s in load_snapshots]
            fail_ratios = [s['fail_ratio'] * 100 for s in load_snapshots]
            
            print(f"\nLoad Generator Statistics:")
            print(f"  Snapshots with load: {len(load_snapshots)}/{len(snapshots)}")
            print(f"  RPS: min={min(rps_values):.1f}, max={max(rps_values):.1f}, avg={statistics.mean(rps_values):.1f}")
            print(f"  Users: min={min(users)}, max={max(users)}, avg={statistics.mean(users):.1f}")
            print(f"  P95 Latency (ms): min={min(p95_values):.0f}, max={max(p95_values):.0f}, avg={statistics.mean(p95_values):.0f}")
            print(f"  Failure Rate (%): min={min(fail_ratios):.2f}, max={max(fail_ratios):.2f}, avg={statistics.mean(fail_ratios):.2f}")
        else:
            print(f"\nLoad Generator: Not available in any snapshot")
        
        # Analyze service metrics
        print(f"\nService Statistics:")
        
        # Get all microservices data
        all_services = set()
        for snapshot in snapshots:
            all_services.update(snapshot['services']['microservices'].keys())
        
        print(f"  Microservices tracked: {len(all_services)}")
        print(f"  Services: {', '.join(sorted(all_services))}")
        
        # CPU stats
        cpu_totals = [s['summary']['total_cpu_percent'] for s in snapshots]
        print(f"\n  Total CPU Usage (%):")
        print(f"    Min: {min(cpu_totals):.1f}, Max: {max(cpu_totals):.1f}, Avg: {statistics.mean(cpu_totals):.1f}")
        
        # Memory stats
        mem_totals = [s['summary']['total_memory_mb'] for s in snapshots]
        print(f"\n  Total Memory Usage (MB):")
        print(f"    Min: {min(mem_totals):.1f}, Max: {max(mem_totals):.1f}, Avg: {statistics.mean(mem_totals):.1f}")
        
        # Network stats
        rx_totals = [s['summary']['total_network_rx_mb'] for s in snapshots]
        tx_totals = [s['summary']['total_network_tx_mb'] for s in snapshots]
        print(f"\n  Total Network RX (MB):")
        print(f"    Min: {min(rx_totals):.1f}, Max: {max(rx_totals):.1f}, Avg: {statistics.mean(rx_totals):.1f}")
        print(f"  Total Network TX (MB):")
        print(f"    Min: {min(tx_totals):.1f}, Max: {max(tx_totals):.1f}, Avg: {statistics.mean(tx_totals):.1f}")
    
    def export_for_ml(self, output_file):
        """Export data in ML-friendly format (flattened time series)"""
        if not self.data:
            return
        
        snapshots = self.data['snapshots']
        ml_data = []
        
        for snapshot in snapshots:
            timestamp = snapshot['timestamp']
            elapsed = snapshot['elapsed_seconds']
            
            # Base record
            record = {
                'timestamp': timestamp,
                'elapsed_seconds': elapsed
            }
            
            # Load generator features
            if snapshot['load_generator']['available']:
                lg = snapshot['load_generator']
                record.update({
                    'load_rps': lg['total_rps'],
                    'load_users': lg['user_count'],
                    'load_fail_ratio': lg['fail_ratio'],
                    'load_p50': lg['response_time_percentiles']['p50'],
                    'load_p75': lg['response_time_percentiles']['p75'],
                    'load_p90': lg['response_time_percentiles']['p90'],
                    'load_p95': lg['response_time_percentiles']['p95'],
                    'load_p99': lg['response_time_percentiles']['p99']
                })
            else:
                record.update({
                    'load_rps': 0,
                    'load_users': 0,
                    'load_fail_ratio': 0,
                    'load_p50': 0,
                    'load_p75': 0,
                    'load_p90': 0,
                    'load_p95': 0,
                    'load_p99': 0
                })
            
            # Summary features
            record.update({
                'total_cpu_percent': snapshot['summary']['total_cpu_percent'],
                'total_memory_mb': snapshot['summary']['total_memory_mb'],
                'total_network_rx_mb': snapshot['summary']['total_network_rx_mb'],
                'total_network_tx_mb': snapshot['summary']['total_network_tx_mb']
            })
            
            # Individual service features
            for service_name, service_data in snapshot['services']['microservices'].items():
                prefix = f'service_{service_name}_'
                record.update({
                    f'{prefix}cpu_percent': service_data['cpu_percent'],
                    f'{prefix}memory_mb': service_data['memory']['usage_mb'],
                    f'{prefix}memory_percent': service_data['memory']['percent'],
                    f'{prefix}network_rx_mb': service_data['network']['rx_mb'],
                    f'{prefix}network_tx_mb': service_data['network']['tx_mb'],
                    f'{prefix}block_read_mb': service_data['block_io']['read_mb'],
                    f'{prefix}block_write_mb': service_data['block_io']['write_mb'],
                    f'{prefix}pids': service_data['pids']
                })
            
            # Infrastructure features
            for service_name, service_data in snapshot['services']['infrastructure'].items():
                prefix = f'infra_{service_name}_'
                record.update({
                    f'{prefix}cpu_percent': service_data['cpu_percent'],
                    f'{prefix}memory_mb': service_data['memory']['usage_mb'],
                    f'{prefix}memory_percent': service_data['memory']['percent']
                })
            
            ml_data.append(record)
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(ml_data, f, indent=2)
        
        print(f"\n✓ Exported {len(ml_data)} records to {output_file}")
        print(f"  Features per record: {len(ml_data[0]) if ml_data else 0}")
        print(f"  File size: {len(json.dumps(ml_data)) / 1024:.1f} KB")
    
    def export_csv(self, output_file):
        """Export data as CSV for easy analysis"""
        if not self.data:
            return
        
        import csv
        
        snapshots = self.data['snapshots']
        
        # Collect all possible field names
        all_fields = set()
        records = []
        
        for snapshot in snapshots:
            record = {
                'timestamp': snapshot['timestamp'],
                'elapsed_seconds': snapshot['elapsed_seconds']
            }
            
            # Load generator
            if snapshot['load_generator']['available']:
                lg = snapshot['load_generator']
                record.update({
                    'load_rps': lg['total_rps'],
                    'load_users': lg['user_count'],
                    'load_fail_ratio': lg['fail_ratio'],
                    'load_p50': lg['response_time_percentiles']['p50'],
                    'load_p95': lg['response_time_percentiles']['p95'],
                    'load_p99': lg['response_time_percentiles']['p99']
                })
            
            # Summary
            record.update({
                'total_cpu': snapshot['summary']['total_cpu_percent'],
                'total_memory_mb': snapshot['summary']['total_memory_mb'],
                'total_net_rx_mb': snapshot['summary']['total_network_rx_mb'],
                'total_net_tx_mb': snapshot['summary']['total_network_tx_mb']
            })
            
            # Services
            for svc, data in snapshot['services']['microservices'].items():
                record[f'{svc}_cpu'] = data['cpu_percent']
                record[f'{svc}_mem_mb'] = data['memory']['usage_mb']
                record[f'{svc}_mem_pct'] = data['memory']['percent']
                record[f'{svc}_net_rx_mb'] = data['network']['rx_mb']
                record[f'{svc}_net_tx_mb'] = data['network']['tx_mb']
            
            all_fields.update(record.keys())
            records.append(record)
        
        # Write CSV
        fieldnames = sorted(all_fields)
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        print(f"\n✓ Exported {len(records)} records to {output_file}")
        print(f"  Columns: {len(fieldnames)}")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze collected metrics JSON data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show summary statistics
  ./metrics_analyzer.py metrics.json
  
  # Export for ML (flattened time series)
  ./metrics_analyzer.py metrics.json --ml-export ml_data.json
  
  # Export as CSV
  ./metrics_analyzer.py metrics.json --csv metrics.csv
  
  # Do all
  ./metrics_analyzer.py metrics.json --ml-export ml_data.json --csv metrics.csv
        """
    )
    
    parser.add_argument('input_file', help='Input JSON file from collect_metrics_json.py')
    parser.add_argument('--ml-export', help='Export ML-friendly JSON to this file')
    parser.add_argument('--csv', help='Export as CSV to this file')
    
    args = parser.parse_args()
    
    analyzer = MetricsAnalyzer(args.input_file)
    
    if not analyzer.load_data():
        sys.exit(1)
    
    analyzer.print_summary()
    
    if args.ml_export:
        analyzer.export_for_ml(args.ml_export)
    
    if args.csv:
        analyzer.export_csv(args.csv)

if __name__ == "__main__":
    main()
