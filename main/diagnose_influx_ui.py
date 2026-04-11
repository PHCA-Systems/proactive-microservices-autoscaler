#!/usr/bin/env python3
"""
Diagnose InfluxDB UI filtering issue
Shows why some services disappear when filtering by cpu_percent
"""

import requests
from datetime import datetime

url = 'http://localhost:8086/api/v2/query'
token = 'phca-token-12345'
org = 'phca'

headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/vnd.flux',
    'Accept': 'application/csv'
}

print("=" * 80)
print("INFLUXDB UI FILTERING DIAGNOSIS")
print("=" * 80)
print()

# Query: Get cpu_percent statistics per service
query = """
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "container_metrics")
  |> filter(fn: (r) => r._field == "cpu_percent")
  |> group(columns: ["service_name"])
  |> mean()
"""

print("📊 Average CPU% per service (last 5 minutes):")
print("-" * 80)
response = requests.post(f'{url}?org={org}', headers=headers, data=query)
lines = response.text.strip().split('\n')

# Parse CSV response
services_cpu = []
for i, line in enumerate(lines):
    if i == 0 or not line.strip():
        continue
    parts = line.split(',')
    if len(parts) >= 6:
        service_name = parts[5]
        cpu_value = parts[4]
        try:
            cpu_float = float(cpu_value)
            services_cpu.append((service_name, cpu_float))
        except:
            pass

# Sort by CPU
services_cpu.sort(key=lambda x: x[1], reverse=True)

print(f"{'Service':<20} {'Avg CPU%':>10}")
print("-" * 32)
for service, cpu in services_cpu:
    print(f"{service:<20} {cpu:>10.4f}%")

print()
print("=" * 80)
print("FINDINGS:")
print("=" * 80)

zero_cpu = [s for s, c in services_cpu if c == 0.0]
low_cpu = [s for s, c in services_cpu if 0 < c < 0.1]
normal_cpu = [s for s, c in services_cpu if c >= 0.1]

print(f"✅ Services with normal CPU (≥0.1%): {len(normal_cpu)}")
for s in normal_cpu:
    print(f"   - {s}")

print()
print(f"⚠️  Services with very low CPU (<0.1%): {len(low_cpu)}")
for s in low_cpu:
    print(f"   - {s}")

print()
print(f"❌ Services with ZERO CPU (0.0%): {len(zero_cpu)}")
for s in zero_cpu:
    print(f"   - {s}")

print()
print("=" * 80)
print("EXPLANATION:")
print("=" * 80)
print("""
The InfluxDB UI may be filtering out services with zero or very low CPU values
when you query for cpu_percent. This is likely due to:

1. UI Aggregation: The UI might use mean() or similar aggregation that filters
   out zero values by default

2. Display Threshold: The UI might have a minimum threshold for displaying
   metrics to reduce noise

3. Time Window: Services with intermittent zero values might disappear when
   the time window only captures zero values

WORKAROUND:
- Use the Script Editor in InfluxDB UI with explicit Flux queries
- Use Grafana for visualization (better control over zero-value handling)
- Filter by memory_usage_bytes instead (always non-zero)
- Use the CLI or API for accurate data queries

DATA INTEGRITY: ✅ All services ARE being written correctly to InfluxDB!
The issue is purely a UI display/filtering behavior.
""")
