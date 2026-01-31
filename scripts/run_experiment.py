#!/usr/bin/env python3
"""
PHCA Experiment Runner
Simple metrics collection with Netdata dashboard
"""

import subprocess
import time
import sys
from datetime import datetime
from simple_metrics_collector import SimpleMetricsCollector

def run_experiment(duration_minutes=10, experiment_name=None):
    """Run a complete PHCA experiment with metrics collection"""
    
    if not experiment_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_name = f"phca_experiment_{timestamp}"
    
    print("🎯 PHCA Simple Experiment")
    print("=" * 50)
    print(f"📊 Experiment: {experiment_name}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print(f"📈 Dashboard: http://localhost:19999")
    print("=" * 50)
    
    # Initialize collector
    collector = SimpleMetricsCollector()
    
    # Check containers
    containers = collector.get_docker_containers()
    if not containers:
        print("❌ No Sock Shop containers found!")
        print("💡 Start Sock Shop first:")
        print("   cd microservices-demo")
        print("   docker-compose up -d")
        return None
    
    print(f"📦 Found {len(containers)} containers")
    
    # Check if Netdata is running
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'netdata' in result.stdout:
            print("✅ Netdata dashboard available at: http://localhost:19999")
        else:
            print("⚠️  Netdata not running - starting it...")
            subprocess.run([
                'docker', 'run', '-d', '--name=netdata', '--pid=host',
                '-v', '/proc:/host/proc:ro',
                '-v', '/sys:/host/sys:ro', 
                '-v', '/var/run/docker.sock:/var/run/docker.sock:ro',
                '--cap-add', 'SYS_PTRACE',
                '--security-opt', 'apparmor=unconfined',
                '-p', '19999:19999',
                'netdata/netdata'
            ])
            time.sleep(10)
            print("✅ Netdata started at: http://localhost:19999")
    except:
        print("⚠️  Could not check Netdata status")
    
    print(f"\n🚀 Starting experiment...")
    print(f"💡 Open http://localhost:19999 to see real-time metrics")
    
    try:
        # Start load test if requested
        load_test_process = None
        if input("\n🔥 Start load test? (y/N): ").lower().startswith('y'):
            print("🔥 Starting load test...")
            load_test_process = subprocess.Popen([
                sys.executable, '-m', 'locust',
                '-f', 'load-testing/src/locustfile_constant.py',
                '--host', 'http://localhost',
                '--users', '10',
                '--spawn-rate', '2',
                '--run-time', f'{duration_minutes}m',
                '--headless'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Collect metrics
        df, filename = collector.collect_metrics(
            duration_minutes=duration_minutes, 
            experiment_id=experiment_name
        )
        
        # Wait for load test to complete
        if load_test_process:
            print("⏳ Waiting for load test to complete...")
            load_test_process.wait()
        
        if df is not None:
            print(f"\n✅ Experiment completed successfully!")
            print(f"📊 Metrics file: {filename}")
            print(f"📈 Total data points: {len(df)}")
            print(f"🎯 Services monitored: {df['service_name'].nunique()}")
            
            # Show summary
            summary = collector.get_service_summary(df)
            if not summary.empty:
                print(f"\n📊 Performance Summary:")
                print("Top CPU users:")
                cpu_summary = summary['cpu_percent']['mean'].sort_values(ascending=False).head(5)
                for service, cpu in cpu_summary.items():
                    print(f"  • {service}: {cpu:.2f}% CPU")
            
            return df, filename
        else:
            print("❌ No metrics collected!")
            return None, None
            
    except KeyboardInterrupt:
        print("\n⚠️  Experiment interrupted by user")
        if load_test_process:
            load_test_process.terminate()
        return None, None
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        return None, None

def main():
    """Main function"""
    
    print("🎯 PHCA Simple Experiment Runner")
    print("=" * 50)
    
    # Get user input
    try:
        duration = input("Enter experiment duration in minutes (default: 5): ").strip()
        duration = int(duration) if duration else 5
        
        experiment_name = input("Enter experiment name (optional): ").strip()
        if not experiment_name:
            experiment_name = None
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return
    
    # Run experiment
    result = run_experiment(duration_minutes=duration, experiment_name=experiment_name)
    
    if result[0] is not None:
        print(f"\n🎉 Experiment completed!")
        print(f"📁 Data saved to: {result[1]}")
        print(f"📈 Dashboard: http://localhost:19999")
    else:
        print(f"\n❌ Experiment failed!")

if __name__ == "__main__":
    main()