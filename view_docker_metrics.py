#!/usr/bin/env python3
"""
Real-Time Docker Metrics Viewer
Shows actual resource usage from Docker stats with Locust traffic info
"""

import subprocess
import json
import sys
import time
from datetime import datetime
import re

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

def clear_screen():
    """Clear the terminal screen"""
    print('\033[2J\033[H', end='')

def get_color_for_value(value, thresholds):
    """Get color based on value and thresholds"""
    if value > thresholds['red']:
        return Colors.RED
    elif value > thresholds['yellow']:
        return Colors.YELLOW
    return Colors.GREEN

def parse_docker_stats():
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
                
                # Parse memory
                mem_str = data['MemUsage'].split('/')[0].strip()
                mem_value = 0.0
                if 'GiB' in mem_str:
                    mem_value = float(mem_str.replace('GiB', '')) * 1024
                elif 'MiB' in mem_str:
                    mem_value = float(mem_str.replace('MiB', ''))
                
                # Parse memory percentage
                mem_perc_str = data['MemPerc'].replace('%', '')
                mem_perc = float(mem_perc_str) if mem_perc_str else 0.0
                
                # Parse network I/O
                net_io = data['NetIO']
                net_parts = net_io.split('/')
                net_in = net_parts[0].strip() if len(net_parts) > 0 else '0B'
                net_out = net_parts[1].strip() if len(net_parts) > 1 else '0B'
                
                stats[name] = {
                    'cpu': cpu,
                    'memory_mb': mem_value,
                    'memory_perc': mem_perc,
                    'net_in': net_in,
                    'net_out': net_out,
                    'block_io': data.get('BlockIO', '0B / 0B')
                }
        
        return stats
    except Exception as e:
        print(f"Error getting Docker stats: {e}")
        return {}

def get_locust_stats():
    """Get Locust statistics"""
    try:
        # Try multiple common Locust ports
        ports = [32852, 32851, 32850, 32823, 32822, 8089]
        result = None
        
        for port in ports:
            try:
                result = subprocess.run(
                    ["curl", "-s", f"http://localhost:{port}/stats/requests"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    break
            except:
                continue
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # Get total stats with safe defaults
            total_rps = data.get('total_rps', 0) or 0
            fail_ratio = data.get('fail_ratio', 0) or 0
            
            # Get percentiles
            percentiles = data.get('current_response_time_percentiles', {})
            p50 = percentiles.get('response_time_percentile_0.5') or 0
            p95 = percentiles.get('response_time_percentile_0.95') or 0
            
            # Get user count
            user_count = data.get('user_count', 0) or 0
            
            return {
                'rps': float(total_rps),
                'fail_ratio': float(fail_ratio) * 100,
                'p50': float(p50),
                'p95': float(p95),
                'users': int(user_count),
                'available': True
            }
    except:
        pass
    
    return {'available': False}

def display_dashboard(docker_stats, locust_stats, update_count):
    """Display the dashboard"""
    clear_screen()
    
    # Header
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 18 + "🚀 REAL-TIME METRICS DASHBOARD" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print(Colors.END)
    
    print(f"{Colors.DIM}Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Updates: {update_count} | Refresh: 5s | Press Ctrl+C to stop{Colors.END}\n")
    
    # Locust Stats
    if locust_stats.get('available'):
        print(f"{Colors.BOLD}{Colors.CYAN}📊 LOAD GENERATOR (LOCUST){Colors.END}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.END}")
        
        try:
            rps = float(locust_stats.get('rps', 0))
            users = int(locust_stats.get('users', 0))
            p50 = float(locust_stats.get('p50', 0))
            p95 = float(locust_stats.get('p95', 0))
            fail = float(locust_stats.get('fail_ratio', 0))
            
            rps_color = Colors.GREEN if rps > 0 else Colors.DIM
            fail_color = Colors.RED if fail > 5 else (Colors.YELLOW if fail > 1 else Colors.GREEN)
            
            print(f"  Active Users: {Colors.BOLD}{users}{Colors.END}")
            print(f"  Total RPS: {rps_color}{rps:.1f} req/s{Colors.END}")
            print(f"  Latency P50: {Colors.CYAN}{p50:.0f} ms{Colors.END}")
            print(f"  Latency P95: {Colors.CYAN}{p95:.0f} ms{Colors.END}")
            print(f"  Failure Rate: {fail_color}{fail:.2f}%{Colors.END}")
            print()
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Error displaying Locust stats: {e}{Colors.END}\n")
    else:
        print(f"{Colors.YELLOW}⚠️  Locust not accessible (checked ports 32852, 32851, 8089){Colors.END}")
        print(f"{Colors.DIM}   Use ./generate_load.py to generate traffic directly{Colors.END}\n")
    
    # Service Stats
    print(f"{Colors.BOLD}{Colors.CYAN}💻 MICROSERVICES RESOURCE USAGE{Colors.END}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.END}\n")
    
    # Filter and sort services
    services = [
        'cart', 'checkout', 'frontend', 'product-catalog', 'recommendation',
        'payment', 'shipping', 'currency', 'email', 'ad', 'accounting', 'fraud-detection'
    ]
    
    # Header
    print(f"{Colors.BOLD}{'SERVICE':<20} {'CPU':>8} {'MEMORY':>12} {'MEM %':>8} {'NET IN':>12} {'NET OUT':>12}{Colors.END}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.END}")
    
    for service in services:
        if service in docker_stats:
            stats = docker_stats[service]
            
            cpu = stats['cpu']
            mem_mb = stats['memory_mb']
            mem_perc = stats['memory_perc']
            net_in = stats['net_in']
            net_out = stats['net_out']
            
            # Color coding
            cpu_color = get_color_for_value(cpu, {'yellow': 60, 'red': 80})
            mem_color = get_color_for_value(mem_perc, {'yellow': 60, 'red': 80})
            
            print(f"{service:<20} "
                  f"{cpu_color}{cpu:>6.1f}%{Colors.END} "
                  f"{Colors.CYAN}{mem_mb:>9.1f} MB{Colors.END} "
                  f"{mem_color}{mem_perc:>6.1f}%{Colors.END} "
                  f"{Colors.DIM}{net_in:>12}{Colors.END} "
                  f"{Colors.DIM}{net_out:>12}{Colors.END}")
        else:
            print(f"{Colors.DIM}{service:<20} {'N/A':>8} {'N/A':>12} {'N/A':>8} {'N/A':>12} {'N/A':>12}{Colors.END}")
    
    # Infrastructure services
    print(f"\n{Colors.BOLD}{Colors.DIM}INFRASTRUCTURE{Colors.END}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.END}")
    
    infra = ['prometheus', 'otel-collector', 'grafana', 'jaeger']
    for service in infra:
        if service in docker_stats:
            stats = docker_stats[service]
            cpu = stats['cpu']
            mem_mb = stats['memory_mb']
            mem_perc = stats['memory_perc']
            
            cpu_color = get_color_for_value(cpu, {'yellow': 60, 'red': 80})
            mem_color = get_color_for_value(mem_perc, {'yellow': 60, 'red': 80})
            
            print(f"{Colors.DIM}{service:<20}{Colors.END} "
                  f"{cpu_color}{cpu:>6.1f}%{Colors.END} "
                  f"{Colors.CYAN}{mem_mb:>9.1f} MB{Colors.END} "
                  f"{mem_color}{mem_perc:>6.1f}%{Colors.END}")
    
    print(f"\n{Colors.DIM}{'─' * 80}{Colors.END}")
    print(f"{Colors.DIM}💡 Tip: Run './generate_load.py' to generate high load{Colors.END}")

def main():
    print(f"{Colors.GREEN}Starting Real-Time Metrics Dashboard...{Colors.END}")
    print(f"{Colors.CYAN}Collecting initial data...{Colors.END}\n")
    time.sleep(2)
    
    update_count = 0
    
    try:
        while True:
            # Get stats
            docker_stats = parse_docker_stats()
            locust_stats = get_locust_stats()
            
            # Display
            display_dashboard(docker_stats, locust_stats, update_count)
            
            update_count += 1
            
            # Wait 5 seconds
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⏹️  Stopping dashboard...{Colors.END}")
        print(f"{Colors.GREEN}✓ Collected {update_count} updates{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}\n")

if __name__ == "__main__":
    main()
