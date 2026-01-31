#!/usr/bin/env python3
"""
PHCA Live Monitor
Real-time display of microservices metrics
"""

import subprocess
import time
import os
from datetime import datetime

def get_docker_stats():
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

def display_metrics(stats):
    """Display metrics in a nice format"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("🎯 PHCA Live Monitor")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | 🔄 Refreshing every 5 seconds")
    print("=" * 60)
    
    if not stats:
        print("⚠️  No services found...")
        return
    
    print(f"{'Service':<15} {'CPU %':<8} {'Memory %':<10}")
    print("-" * 40)
    
    # Sort by CPU usage
    sorted_services = sorted(stats.items(), key=lambda x: x[1]['cpu'], reverse=True)
    
    for service, metrics in sorted_services:
        cpu = f"{metrics['cpu']:.2f}"
        mem = f"{metrics['mem']:.2f}"
        print(f"{service:<15} {cpu:<8} {mem:<10}")
    
    print("\n" + "=" * 60)
    print("🔥 Top CPU Users:")
    for i, (service, metrics) in enumerate(sorted_services[:3], 1):
        if metrics['cpu'] > 0:
            print(f"  {i}. {service}: {metrics['cpu']:.2f}% CPU")
    
    print(f"\n📊 Total Services: {len(stats)}")
    print("💡 Press Ctrl+C to stop")

def main():
    """Main monitoring loop"""
    print("🚀 Starting PHCA Live Monitor...")
    
    try:
        while True:
            stats = get_docker_stats()
            display_metrics(stats)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped")

if __name__ == "__main__":
    main()