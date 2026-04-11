# 📊 InfluxDB Queries - Ready to Use

## How to Use These Queries

### In InfluxDB Web UI (http://localhost:8086)
1. Login: admin / password123
2. Click "Data Explorer" (left sidebar)
3. Click "Script Editor" (top right)
4. Paste any query below
5. Click "Submit"

### In Grafana (http://localhost:3000)
1. Login: admin / admin
2. Go to "Explore" (left sidebar)
3. Select "InfluxDB" data source
4. Paste query and click "Run Query"

---

## 🎯 Essential Per-Service Queries

### 1. CPU Usage by Service (Last 30 Minutes)
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

### 2. Memory Usage by Service (MB)
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_bytes")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

### 3. Current Service Status (Last 5 Minutes)
```flux
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> last()
  |> yield(name: "current_cpu")
```

### 4. Network I/O by Service
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "network_rx_bytes" or r["_field"] == "network_tx_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 2m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

### 5. Top 5 CPU Consumers (Current)
```flux
from(bucket: "microservices")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> mean()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 5)
```

### 6. Memory Usage Percentage by Service
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

### 7. Disk I/O by Service (MB)
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "block_read_bytes" or r["_field"] == "block_write_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 2m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

---

## 🔍 Diagnostic Queries

### 8. Check Available Data (How Many Records?)
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> count()
```

### 9. List All Services Being Monitored
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> distinct(column: "service_name")
  |> group()
  |> sort(columns: ["service_name"])
```

### 10. Latest Data Timestamp (When Was Last Collection?)
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
```

---

## 📈 Advanced Analysis Queries

### 11. Service Resource Correlation (CPU vs Memory)
```flux
cpu_data = from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

memory_data = from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

join(tables: {cpu: cpu_data, memory: memory_data}, on: ["_time", "service_name"])
```

### 12. Service Performance Summary (Last Hour)
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent" or r["_field"] == "memory_usage_percent")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 10m, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time", "service_name"], columnKey: ["_field"], valueColumn: "_value")
```

### 13. Network Traffic Patterns
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "network_rx_bytes" or r["_field"] == "network_tx_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> derivative(unit: 1m, nonNegative: true)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 }))
```

---

## 🚨 Troubleshooting

### If Queries Return No Data:
1. **Check data collection**: Run `python influx_collector.py` (option 1)
2. **Verify time range**: Change `-30m` to `-1h` or `-2h`
3. **Check bucket name**: Ensure "microservices" bucket exists
4. **Verify measurement**: Should be "container_metrics"

### If Grafana Shows No Data:
1. **Check data source**: Configuration → Data Sources → InfluxDB → Test
2. **Verify query syntax**: Use these exact queries in Grafana Explore
3. **Check time range**: Set Grafana time range to "Last 1 hour"
4. **Refresh data**: Click refresh button in Grafana

### Expected Services (14 total):
- edge-router, front-end, catalogue, catalogue-db
- carts, carts-db, orders, orders-db
- shipping, queue-master, rabbitmq, payment
- user, user-db

---

## 🎯 Quick Test Sequence

**Step 1**: Run Query #8 (Check Available Data)
- Should show > 0 records

**Step 2**: Run Query #9 (List All Services)
- Should show 14 services

**Step 3**: Run Query #3 (Current Service Status)
- Should show recent CPU data for each service

**Step 4**: Run Query #1 (CPU Usage by Service)
- Should show time-series graph in Grafana