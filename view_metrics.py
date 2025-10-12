#!/usr/bin/env python3
"""
Real-Time Metrics Viewer
Beautiful, readable display of ML training metrics in the terminal
"""

import subprocess
import json
import sys
import time
from datetime import datetime
from collections import defaultdict, deque
import argparse

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    DIM = '\033[2m'

def clear_screen():
    """Clear the terminal screen"""
    print('\033[2J\033[H', end='')

def format_number(value, decimals=2):
    """Format number with appropriate precision"""
    if isinstance(value, int):
        return str(value)
    if value == 0:
        return "0"
    if value < 0.01:
        return f"{value:.4f}"
    return f"{value:.{decimals}f}"

def get_status_color(metric_name, value):
    """Get color based on metric value"""
    if metric_name in ['error_rate']:
        if value > 5:
            return Colors.RED
        elif value > 1:
            return Colors.YELLOW
        return Colors.GREEN
    elif metric_name in ['cpu_percent', 'memory_utilization_percent']:
        if value > 80:
            return Colors.RED
        elif value > 60:
            return Colors.YELLOW
        return Colors.GREEN
    elif metric_name in ['latency_p95_ms', 'latency_p99_ms']:
        if value > 100:
            return Colors.RED
        elif value > 50:
            return Colors.YELLOW
        return Colors.GREEN
    return Colors.CYAN

def format_metric_value(metric_name, value):
    """Format metric with color and units"""
    color = get_status_color(metric_name, value)
    formatted = format_number(value)
    
    # Add units
    if 'percent' in metric_name or 'rate' in metric_name:
        return f"{color}{formatted}%{Colors.END}"
    elif 'mb' in metric_name.lower():
        return f"{color}{formatted} MB{Colors.END}"
    elif 'ms' in metric_name:
        return f"{color}{formatted} ms{Colors.END}"
    elif 'per_sec' in metric_name:
        return f"{color}{formatted}/s{Colors.END}"
    else:
        return f"{color}{formatted}{Colors.END}"

class MetricsViewer:
    def __init__(self, service_filter=None, compact=False):
        self.service_filter = service_filter
        self.compact = compact
        self.metrics_history = defaultdict(lambda: deque(maxlen=10))
        self.last_update = {}
        self.update_count = 0
        
    def format_service_header(self, service):
        """Format service name header"""
        return f"{Colors.BOLD}{Colors.BLUE}{'='*80}\n  {service.upper()}\n{'='*80}{Colors.END}"
    
    def format_section(self, title, metrics_dict, data):
        """Format a section of metrics"""
        lines = [f"\n{Colors.BOLD}{Colors.CYAN}{title}:{Colors.END}"]
        
        for key, label in metrics_dict.items():
            if key in data:
                value = data[key]
                formatted_value = format_metric_value(key, value)
                lines.append(f"  {Colors.DIM}{label:.<30}{Colors.END} {formatted_value}")
        
        return '\n'.join(lines)
    
    def display_full_metrics(self, data):
        """Display full detailed metrics"""
        output = []
        
        # Header
        output.append(self.format_service_header(data['service']))
        output.append(f"{Colors.DIM}Timestamp: {data['timestamp']}{Colors.END}")
        
        # Performance Metrics
        perf_metrics = {
            'rps': 'Requests/sec',
            'latency_p50_ms': 'Latency P50',
            'latency_p95_ms': 'Latency P95',
            'latency_p99_ms': 'Latency P99',
            'latency_mean_ms': 'Latency Mean',
            'error_rate': 'Error Rate',
            'success_rate': 'Success Rate',
        }
        output.append(self.format_section('⚡ PERFORMANCE', perf_metrics, data))
        
        # Resource Utilization
        resource_metrics = {
            'cpu_percent': 'CPU Usage',
            'memory_mb': 'Memory',
            'memory_utilization_percent': 'Memory Utilization',
            'disk_io_mb_per_sec': 'Disk I/O',
            'network_io_mb_per_sec': 'Network I/O',
        }
        output.append(self.format_section('💻 RESOURCES', resource_metrics, data))
        
        # Application Metrics
        app_metrics = {
            'active_connections': 'Active Connections',
            'queue_depth': 'Queue Depth',
            'thread_count': 'Threads',
            'gc_collections_per_sec': 'GC Collections/sec',
        }
        output.append(self.format_section('🔧 APPLICATION', app_metrics, data))
        
        # Scaling Context
        scaling_metrics = {
            'replica_count': 'Replicas',
            'resource_efficiency_score': 'Efficiency Score',
            'throughput_mb_per_sec': 'Throughput',
        }
        output.append(self.format_section('📊 SCALING', scaling_metrics, data))
        
        output.append('')
        return '\n'.join(output)
    
    def display_compact_metrics(self, data):
        """Display compact single-line metrics"""
        service = data['service']
        rps = data['rps']
        cpu = data['cpu_percent']
        mem = data['memory_utilization_percent']
        lat_p95 = data['latency_p95_ms']
        err = data['error_rate']
        
        # Format with colors
        rps_str = format_metric_value('rps', rps)
        cpu_str = format_metric_value('cpu_percent', cpu)
        mem_str = format_metric_value('memory_utilization_percent', mem)
        lat_str = format_metric_value('latency_p95_ms', lat_p95)
        err_str = format_metric_value('error_rate', err)
        
        return f"{Colors.BOLD}{service:.<20}{Colors.END} RPS:{rps_str:>12} CPU:{cpu_str:>10} MEM:{mem_str:>10} P95:{lat_str:>12} ERR:{err_str:>10}"
    
    def display_dashboard(self, all_metrics):
        """Display dashboard with all services"""
        clear_screen()
        
        # Header
        print(f"{Colors.BOLD}{Colors.HEADER}")
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🤖 ML METRICS LIVE DASHBOARD" + " " * 29 + "║")
        print("╚" + "═" * 78 + "╝")
        print(Colors.END)
        
        print(f"{Colors.DIM}Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Updates: {self.update_count} | Press Ctrl+C to stop{Colors.END}\n")
        
        if self.compact:
            # Compact view - all services on screen
            print(f"{Colors.BOLD}{Colors.CYAN}SERVICE OVERVIEW{Colors.END}")
            print(f"{Colors.DIM}{'─' * 80}{Colors.END}\n")
            
            for service, data in sorted(all_metrics.items()):
                print(self.display_compact_metrics(data))
        else:
            # Full view - one service at a time
            if all_metrics:
                service = list(all_metrics.keys())[0]
                print(self.display_full_metrics(all_metrics[service]))
    
    def process_line(self, line):
        """Process a single metrics line"""
        try:
            data = json.loads(line.strip())
            
            if 'service' not in data or 'timestamp' not in data:
                return None
            
            # Apply service filter
            if self.service_filter and data['service'] != self.service_filter:
                return None
            
            service = data['service']
            self.last_update[service] = data
            self.update_count += 1
            
            return service
            
        except json.JSONDecodeError:
            return None
    
    def run(self, container_name='metrics-collector'):
        """Run the viewer"""
        try:
            # Start docker logs
            cmd = ["docker", "logs", "-f", "--tail", "0", container_name]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"{Colors.GREEN}✓ Connected to {container_name}{Colors.END}")
            print(f"{Colors.CYAN}Loading metrics...{Colors.END}\n")
            time.sleep(2)
            
            last_display = time.time()
            display_interval = 1.0  # Update display every second
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                self.process_line(line)
                
                # Update display periodically
                now = time.time()
                if now - last_display >= display_interval and self.last_update:
                    self.display_dashboard(self.last_update)
                    last_display = now
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⏹️  Stopping viewer...{Colors.END}")
            process.terminate()
        except Exception as e:
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")

def main():
    parser = argparse.ArgumentParser(
        description='Real-time metrics viewer with beautiful formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full detailed view
  python3 view_metrics.py
  
  # Compact view (all services)
  python3 view_metrics.py --compact
  
  # Filter specific service
  python3 view_metrics.py -s cart
  
  # Compact view for specific service
  python3 view_metrics.py -s frontend --compact
        """
    )
    
    parser.add_argument('-s', '--service',
                       help='Filter by specific service')
    parser.add_argument('-c', '--container',
                       default='metrics-collector',
                       help='Docker container name')
    parser.add_argument('--compact',
                       action='store_true',
                       help='Compact view (all services on one screen)')
    
    args = parser.parse_args()
    
    viewer = MetricsViewer(
        service_filter=args.service,
        compact=args.compact
    )
    
    viewer.run(args.container)

if __name__ == "__main__":
    main()
