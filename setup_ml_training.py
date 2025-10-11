#!/usr/bin/env python3
"""
Setup script for ML training data collection.
Ensures all components are running and configured correctly.
"""

import subprocess
import time
import sys
import os
import requests
from datetime import datetime

def run_command(cmd, check=True):
    """Run a shell command"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def check_service(url, name, timeout=30):
    """Check if a service is responding"""
    print(f"Checking {name} at {url}...")
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name} is running")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < timeout - 1:
            print(f"  Waiting for {name}... ({i+1}/{timeout})")
            time.sleep(1)
    
    print(f"✗ {name} is not responding")
    return False

def main():
    print("=== ML Training Data Collection Setup ===\n")
    
    # Check if Docker is running
    print("1. Checking Docker...")
    if not run_command("docker --version", check=False):
        print("Error: Docker is not installed or not running")
        sys.exit(1)
    
    if not run_command("docker-compose --version", check=False):
        print("Error: Docker Compose is not installed")
        sys.exit(1)
    
    # Create necessary directories
    print("\n2. Creating directories...")
    os.makedirs("logs", exist_ok=True)
    print("✓ Created logs directory")
    
    # Build the metrics collector
    print("\n3. Building metrics collector...")
    if not run_command("docker-compose build metrics-collector"):
        print("Error: Failed to build metrics collector")
        sys.exit(1)
    
    # Start the core services
    print("\n4. Starting core services...")
    services = [
        "prometheus", "grafana", "otel-collector", 
        "cart", "checkout", "frontend", "product-catalog"
    ]
    
    for service in services:
        print(f"Starting {service}...")
        if not run_command(f"docker-compose up -d {service}"):
            print(f"Warning: Failed to start {service}")
    
    # Wait for services to be ready
    print("\n5. Waiting for services to be ready...")
    time.sleep(10)
    
    # Check service health
    print("\n6. Checking service health...")
    services_to_check = [
        ("http://localhost:9090/-/ready", "Prometheus"),
        ("http://localhost:3000/api/health", "Grafana"),
        ("http://localhost:8080", "Frontend")
    ]
    
    all_healthy = True
    for url, name in services_to_check:
        if not check_service(url, name):
            all_healthy = False
    
    if not all_healthy:
        print("\nWarning: Some services are not responding. Continuing anyway...")
    
    # Start metrics collector
    print("\n7. Starting metrics collector...")
    if not run_command("docker-compose up -d metrics-collector"):
        print("Error: Failed to start metrics collector")
        sys.exit(1)
    
    # Wait for metrics collector to start
    time.sleep(5)
    
    # Start load generator
    print("\n8. Starting load generator...")
    if not run_command("docker-compose up -d load-generator"):
        print("Warning: Failed to start load generator")
    
    print("\n=== Setup Complete ===")
    print("\nNext steps:")
    print("1. Access Grafana at http://localhost:3000 (admin/admin)")
    print("2. Access Locust at http://localhost:8089 to generate load")
    print("3. Start collecting metrics:")
    print("   python src/metrics-collector/stream_logs.py --output logs/training_data.jsonl")
    print("4. Analyze collected data:")
    print("   python analyze_metrics.py logs/training_data.jsonl")
    
    print(f"\nSetup completed at: {datetime.now()}")
    
    # Show running containers
    print("\nRunning containers:")
    run_command("docker-compose ps", check=False)

if __name__ == "__main__":
    main()