#!/usr/bin/env python3
"""Test InfluxDB queries to understand why services disappear in UI"""

import requests

url = 'http://localhost:8086/api/v2/query'
token = 'phca-token-12345'
org = 'phca'

# Query 1: Get all unique service names with cpu_percent in last 5 minutes
query1 = """
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "container_metrics")
  |> filter(fn: (r) => r._field == "cpu_percent")
  |> group(columns: ["service_name"])
  |> distinct(column: "service_name")
"""

# Query 2: Get last cpu_percent value for each service
query2 = """
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "container_metrics")
  |> filter(fn: (r) => r._field == "cpu_percent")
  |> group(columns: ["service_name"])
  |> last()
"""

# Query 3: Count data points per service
query3 = """
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "container_metrics")
  |> filter(fn: (r) => r._field == "cpu_percent")
  |> group(columns: ["service_name"])
  |> count()
"""

# Query 4: Get services with memory_usage_bytes
query4 = """
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "container_metrics")
  |> filter(fn: (r) => r._field == "memory_usage_bytes")
  |> group(columns: ["service_name"])
  |> last()
"""

headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/vnd.flux',
    'Accept': 'application/csv'
}

print("=" * 80)
print("QUERY 1: Unique service names with cpu_percent (last 5m)")
print("=" * 80)
response = requests.post(f'{url}?org={org}', headers=headers, data=query1)
print(response.text)
print()

print("=" * 80)
print("QUERY 2: Last cpu_percent value per service (last 5m)")
print("=" * 80)
response = requests.post(f'{url}?org={org}', headers=headers, data=query2)
lines = response.text.strip().split('\n')
for line in lines:
    print(line)
print()

print("=" * 80)
print("QUERY 3: Count of cpu_percent data points per service (last 5m)")
print("=" * 80)
response = requests.post(f'{url}?org={org}', headers=headers, data=query3)
lines = response.text.strip().split('\n')
for line in lines:
    print(line)
print()

print("=" * 80)
print("QUERY 4: Last memory_usage_bytes value per service (last 5m)")
print("=" * 80)
response = requests.post(f'{url}?org={org}', headers=headers, data=query4)
lines = response.text.strip().split('\n')
for line in lines:
    print(line)
print()
