#!/usr/bin/env python3
"""
Test Grafana InfluxDB Connection
"""

import requests
import json
from influxdb_client import InfluxDBClient

def test_direct_influx_query():
    """Test direct InfluxDB query to verify data exists"""
    print("🔍 Testing Direct InfluxDB Query...")
    
    try:
        client = InfluxDBClient(
            url="http://localhost:8086",
            token="phca-token-12345",
            org="phca"
        )
        
        query_api = client.query_api()
        
        # Simple test query
        query = '''
        from(bucket: "microservices")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "container_metrics")
          |> filter(fn: (r) => r["_field"] == "cpu_percent")
          |> group(columns: ["service_name"])
          |> last()
        '''
        
        result = query_api.query(org="phca", query=query)
        
        services_found = []
        for table in result:
            for record in table.records:
                service_name = record.values.get("service_name")
                cpu_value = record.get_value()
                time_stamp = record.get_time()
                
                if service_name:
                    services_found.append({
                        'service': service_name,
                        'cpu': cpu_value,
                        'time': time_stamp
                    })
        
        print(f"✅ Found {len(services_found)} services with recent data:")
        for service in sorted(services_found, key=lambda x: x['service'])[:5]:
            print(f"   • {service['service']}: {service['cpu']:.2f}% CPU at {service['time']}")
        
        if len(services_found) > 5:
            print(f"   ... and {len(services_found)-5} more")
        
        client.close()
        return len(services_found) > 0
        
    except Exception as e:
        print(f"❌ Direct InfluxDB query failed: {e}")
        return False

def create_grafana_test_query():
    """Create a simple Grafana-compatible query"""
    print("\n📋 Grafana Query to Test:")
    print("=" * 50)
    
    query = '''from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)'''
    
    print(query)
    print("=" * 50)
    print("\n📝 Instructions for Grafana:")
    print("1. Go to http://localhost:3000")
    print("2. Login: admin / admin")
    print("3. Click 'Explore' (compass icon)")
    print("4. Select 'InfluxDB' data source")
    print("5. Paste the query above")
    print("6. Set time range to 'Last 1 hour'")
    print("7. Click 'Run Query'")
    
    return query

def main():
    """Main test function"""
    print("🎯 Grafana Connection Test")
    print("=" * 40)
    
    # Test direct InfluxDB access
    data_exists = test_direct_influx_query()
    
    if data_exists:
        print("\n✅ Data exists in InfluxDB!")
        create_grafana_test_query()
        
        print(f"\n💡 Grafana Troubleshooting Tips:")
        print(f"• Make sure time range is set to 'Last 1 hour' or more")
        print(f"• Check that InfluxDB data source is selected")
        print(f"• Try refreshing the page if no data appears")
        print(f"• Verify the query syntax matches exactly")
        
    else:
        print("\n❌ No data found in InfluxDB!")
        print("💡 Run data collection first:")
        print("   python influx_collector.py")
        print("   Choose option 2 (collect for 5 minutes)")

if __name__ == "__main__":
    main()