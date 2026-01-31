#!/usr/bin/env python3
"""
Quick InfluxDB Queries - Copy & Paste Ready
"""

def print_queries():
    """Print all queries ready for copy-paste"""
    
    queries = {
        "1. Current Service Status (Last 5 min)": '''from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> last()''',

        "2. CPU Usage by Service (30 min)": '''from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)''',

        "3. Memory Usage (MB) by Service": '''from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_bytes")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))''',

        "4. Top 5 CPU Users": '''from(bucket: "microservices")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> mean()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 5)''',

        "5. Network I/O (MB) by Service": '''from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "network_rx_bytes" or r["_field"] == "network_tx_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 2m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))''',

        "6. GRAFANA QUERY (Use in Grafana Explore)": '''from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)''',

        "7. Check How Much Data We Have": '''from(bucket: "microservices")
  |> range(start: -2h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> count()''',

        "8. List All Services": '''from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> distinct(column: "service_name")
  |> group()
  |> sort(columns: ["service_name"])'''
    }
    
    print("🎯 PHCA InfluxDB Queries - Ready to Copy & Paste")
    print("=" * 60)
    print("\n📍 Where to use:")
    print("• InfluxDB Web UI: http://localhost:8086 → Data Explorer → Script Editor")
    print("• Grafana: http://localhost:3000 → Explore → InfluxDB")
    print("\n" + "=" * 60)
    
    for title, query in queries.items():
        print(f"\n### {title}")
        print("-" * 50)
        print(query)
        print("-" * 50)
    
    print(f"\n💡 Tips:")
    print(f"• For Grafana: Use query #6 (has v.timeRangeStart variables)")
    print(f"• For InfluxDB UI: Use queries #1-5, #7-8 (fixed time ranges)")
    print(f"• Start with query #7 to check if you have data")
    print(f"• Then try query #8 to see your services")
    print(f"• Finally use query #2 for a nice CPU graph")

if __name__ == "__main__":
    print_queries()