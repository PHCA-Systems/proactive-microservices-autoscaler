#!/usr/bin/env python3
"""
PHCA Environment Setup
Sets up the complete monitoring environment for PHCA research
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description, cwd=None):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, cwd=cwd)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def check_docker():
    """Check if Docker is running"""
    try:
        subprocess.run(["docker", "ps"], check=True, capture_output=True)
        print("✅ Docker is running")
        return True
    except:
        print("❌ Docker is not running. Please start Docker Desktop.")
        return False

def setup_sock_shop():
    """Set up Sock Shop microservices"""
    print("\n🏪 Setting up Sock Shop microservices...")
    
    sock_shop_path = Path("microservices-demo")
    if not sock_shop_path.exists():
        print("❌ Sock Shop not found. Please clone the repository first.")
        return False
    
    return run_command(
        ["docker-compose", "up", "-d"],
        "Starting Sock Shop services",
        cwd=sock_shop_path
    )

def setup_monitoring_stack():
    """Set up InfluxDB + Grafana monitoring stack"""
    print("\n📊 Setting up monitoring stack...")
    
    influx_path = Path("influx-stack")
    if not influx_path.exists():
        print("❌ InfluxDB stack not found")
        return False
    
    return run_command(
        ["docker-compose", "up", "-d"],
        "Starting InfluxDB + Grafana",
        cwd=influx_path
    )

def wait_for_services():
    """Wait for services to be ready"""
    print("\n⏳ Waiting for services to start...")
    time.sleep(30)
    
    # Check Sock Shop
    try:
        import requests
        response = requests.get("http://localhost:80", timeout=5)
        if response.status_code == 200:
            print("✅ Sock Shop is ready")
        else:
            print("⚠️  Sock Shop may not be fully ready")
    except:
        print("⚠️  Sock Shop not responding")
    
    # Check InfluxDB
    try:
        import requests
        response = requests.get("http://localhost:8086/health", timeout=5)
        if response.status_code == 200:
            print("✅ InfluxDB is ready")
        else:
            print("⚠️  InfluxDB may not be ready")
    except:
        print("⚠️  InfluxDB not responding")

def main():
    """Main setup function"""
    print("🎯 PHCA Environment Setup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_docker():
        sys.exit(1)
    
    # Setup services
    if not setup_sock_shop():
        print("❌ Failed to set up Sock Shop")
        sys.exit(1)
    
    if not setup_monitoring_stack():
        print("❌ Failed to set up monitoring stack")
        sys.exit(1)
    
    # Wait and verify
    wait_for_services()
    
    print("\n🎉 Environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Sock Shop: http://localhost:80")
    print("2. Grafana: http://localhost:3000 (admin/admin)")
    print("3. InfluxDB: http://localhost:8086 (admin/password123)")
    print("4. Start metrics collection: python collectors/phca_metrics_collector.py")
    print("5. Start load testing: python load-testing/scripts/run_load_test.py")

if __name__ == "__main__":
    main()