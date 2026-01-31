#!/usr/bin/env python3
"""
PHCA Monitoring Stack Verification
Quick verification that InfluxDB and Grafana are working correctly
"""

import requests
import json
from influxdb_client import InfluxDBClient

def test_influxdb():
    """Test InfluxDB connection and data"""
    print("🔍 Testing InfluxDB...")
    
    try:
        # Health check
        response = requests.get("http://localhost:8086/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ InfluxDB Health: {health['status']} - {health['message']}")
        else:
            print(f"❌ InfluxDB Health Check Failed: {response.status_code}")
            return False
        
        # Data check
        client = InfluxDBClient(
            url="http://localhost:8086",
            token="phca-token-12345",
            org="phca"
        )
        
        query_api = client.query_api()
        query = '''
        from(bucket: "microservices")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "container_metrics")
          |> count()
        '''
        
        result = query_api.query(org="phca", query=query)
        
        total_records = 0
        for table in result:
            for record in table.records:
                total_records += record.get_value()
        
        print(f"✅ InfluxDB Data: {total_records} records in last hour")
        
        # Service check
        service_query = '''
        from(bucket: "microservices")
          |> range(start: -10m)
          |> filter(fn: (r) => r["_measurement"] == "container_metrics")
          |> filter(fn: (r) => r["_field"] == "cpu_percent")
          |> group(columns: ["service_name"])
          |> distinct(column: "service_name")
          |> count()
        '''
        
        service_result = query_api.query(org="phca", query=service_query)
        services = []
        for table in service_result:
            for record in table.records:
                service_name = record.values.get("service_name")
                if service_name:
                    services.append(service_name)
        
        print(f"✅ Active Services: {len(services)} services monitored")
        for service in sorted(services)[:5]:
            print(f"   • {service}")
        if len(services) > 5:
            print(f"   ... and {len(services)-5} more")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ InfluxDB Test Failed: {e}")
        return False

def test_grafana():
    """Test Grafana connection"""
    print("\n🔍 Testing Grafana...")
    
    try:
        # Basic connectivity
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Grafana Web UI: Accessible on http://localhost:3000")
        else:
            print(f"❌ Grafana Web UI: Failed ({response.status_code})")
            return False
        
        # Try to check API (will fail without auth, but shows it's running)
        api_response = requests.get("http://localhost:3000/api/health", timeout=5)
        if api_response.status_code in [200, 401]:
            print("✅ Grafana API: Running")
        else:
            print(f"⚠️  Grafana API: Unexpected response ({api_response.status_code})")
        
        return True
        
    except Exception as e:
        print(f"❌ Grafana Test Failed: {e}")
        return False

def test_docker_containers():
    """Test if Sock Shop containers are running"""
    print("\n🔍 Testing Sock Shop Containers...")
    
    try:
        import subprocess
        result = subprocess.run([
            'docker', 'ps', '--format', '{{.Names}}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            sock_shop_containers = [c for c in containers if 'docker-compose' in c]
            
            print(f"✅ Docker Containers: {len(sock_shop_containers)} Sock Shop services running")
            
            # Show some examples
            for container in sorted(sock_shop_containers)[:5]:
                service_name = container.replace('docker-compose-', '').replace('-1', '')
                print(f"   • {service_name}")
            
            if len(sock_shop_containers) > 5:
                print(f"   ... and {len(sock_shop_containers)-5} more")
            
            return len(sock_shop_containers) > 0
        else:
            print(f"❌ Docker Command Failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Docker Test Failed: {e}")
        return False

def main():
    """Main verification function"""
    print("🎯 PHCA Monitoring Stack Verification")
    print("=" * 50)
    
    # Test all components
    influx_ok = test_influxdb()
    grafana_ok = test_grafana()
    docker_ok = test_docker_containers()
    
    print("\n📊 Verification Summary")
    print("=" * 30)
    print(f"InfluxDB:     {'✅ PASS' if influx_ok else '❌ FAIL'}")
    print(f"Grafana:      {'✅ PASS' if grafana_ok else '❌ FAIL'}")
    print(f"Containers:   {'✅ PASS' if docker_ok else '❌ FAIL'}")
    
    if all([influx_ok, grafana_ok, docker_ok]):
        print("\n🎉 All systems operational!")
        print("\n📋 Next Steps:")
        print("1. Open Grafana: http://localhost:3000 (admin/admin)")
        print("2. Open InfluxDB: http://localhost:8086 (admin/password123)")
        print("3. Run data collection: python influx_collector.py")
        print("4. Create Grafana dashboards using the queries in CHECKPOINT_INFLUXDB_GRAFANA.md")
    else:
        print("\n⚠️  Some components need attention!")
        print("Check the error messages above and refer to CHECKPOINT_INFLUXDB_GRAFANA.md")

if __name__ == "__main__":
    main()