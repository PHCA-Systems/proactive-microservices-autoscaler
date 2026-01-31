#!/usr/bin/env python3
"""
PHCA Prometheus Experiment Runner
Runs load testing while collecting metrics using Prometheus + Docker stats
"""

import subprocess
import time
import sys
import os
from datetime import datetime

# Add monitoring-stack to path
sys.path.append('monitoring-stack')
from setup_monitoring import PHCAPrometheusCollector

def run_experiment(duration_minutes=10, experiment_name=None):
    """Run a complete PHCA experiment with load testing and metrics collection"""
    
    if not experiment_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_name = f"phca_experiment_{timestamp}"
    
    print("🎯 PHCA Prometheus Experiment")
    print("=" * 50)
    print(f"📊 Experiment: {experiment_name}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print("=" * 50)
    
    # Initialize collector
    collector = PHCAPrometheusCollector()
    
    # Check containers
    containers = collector.get_docker_containers()
    if not containers:
        print("❌ No Sock Shop containers found!")
        print("💡 Start Sock Shop first:")
        print("   cd microservices-demo")
        print("   docker-compose up -d")
        return None
    
    print(f"📦 Found {len(containers)} containers")
    
    # Start metrics collection in background
    print("\n🚀 Starting metrics collection...")
    
    try:
        # Start load test
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
        
        # Collect metrics while load test runs
        df, filename = collector.collect_hybrid_metrics(
            duration_minutes=duration_minutes, 
            experiment_id=experiment_name
        )
        
        # Wait for load test to complete
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
                cpu_summary = summary['cpu_percent_docker']['mean'].sort_values(ascending=False).head(5)
                for service, cpu in cpu_summary.items():
                    print(f"  • {service}: {cpu:.2f}% CPU")
            
            return df, filename
        else:
            print("❌ No metrics collected!")
            return None, None
            
    except KeyboardInterrupt:
        print("\n⚠️  Experiment interrupted by user")
        if 'load_test_process' in locals():
            load_test_process.terminate()
        return None, None
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        return None, None

def main():
    """Main function"""
    
    print("🎯 PHCA Prometheus Experiment Runner")
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
        print(f"🌐 View Prometheus: http://localhost:9090")
        print(f"📊 View Grafana: http://localhost:3000")
    else:
        print(f"\n❌ Experiment failed!")

if __name__ == "__main__":
    main()