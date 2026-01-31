# PHCA Monitoring Stack Checkpoint

## Current Status ✅
- **InfluxDB**: Running and healthy with 224 records
- **Grafana**: Running on port 3000
- **Data Collection**: Working via `influx_collector.py`
- **Sock Shop**: 14 microservices running and monitored

## InfluxDB Verification

### 1. Health Check
```bash
# PowerShell
Invoke-WebRequest -Uri "http://localhost:8086/health" -Method GET -UseBasicParsing

# Expected: {"name":"influxdb","message":"ready for queries and writes","status":"pass"}
```

### 2. Web UI Access
- **URL**: http://localhost:8086
- **Username**: admin
- **Password**: password123
- **Organization**: phca
- **Bucket**: microservices
- **Token**: phca-token-12345

### 3. Data Verification Queries (Run in InfluxDB Web UI)

#### Basic Data Check
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> count()
```

#### Service Overview
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> mean()
```

#### CPU Usage by Service
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

#### Memory Usage by Service
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_bytes")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

#### Network I/O by Service
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "network_rx_bytes" or r["_field"] == "network_tx_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

#### Top CPU Consumers
```flux
from(bucket: "microservices")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> mean()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 5)
```

#### Memory Usage Percentage
```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

## Grafana Verification

### 1. Access Grafana
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin

### 2. Check InfluxDB Data Source
1. Go to Configuration → Data Sources
2. Should see "InfluxDB" configured
3. Click "Test" button - should show "Data source is working"

### 3. Create Test Dashboard
1. Click "+" → Dashboard
2. Add Panel
3. Select InfluxDB as data source
4. Use this query:
```flux
from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

### 4. Verify Data Flow
- Should see real-time data from all 14 Sock Shop services
- Data should update every 5 seconds (our collection interval)
- Services: front-end, catalogue, carts, orders, shipping, payment, user, etc.

## Data Collection Commands

### Manual Collection (5 minutes)
```bash
python influx_collector.py
# Choose option 2
```

### Query Recent Data
```bash
python influx_collector.py
# Choose option 3
```

### Test Connection Only
```bash
python influx_collector.py
# Choose option 1
```

## Available Metrics per Container
- **cpu_percent**: CPU usage percentage
- **memory_usage_bytes**: Memory usage in bytes
- **memory_limit_bytes**: Memory limit in bytes
- **memory_usage_percent**: Memory usage percentage
- **network_rx_bytes**: Network received bytes
- **network_tx_bytes**: Network transmitted bytes
- **block_read_bytes**: Disk read bytes
- **block_write_bytes**: Disk write bytes
- **pids**: Number of processes

## Container Services Being Monitored
1. edge-router
2. front-end
3. catalogue
4. catalogue-db
5. carts
6. carts-db
7. orders
8. orders-db
9. shipping
10. queue-master
11. rabbitmq
12. payment
13. user
14. user-db

## Next Steps for Linux Migration
1. **Telegraf**: Will work properly on Linux with Docker socket access
2. **Professional Setup**: Telegraf → InfluxDB → Grafana pipeline
3. **Advanced Queries**: More complex Flux queries for ML feature extraction
4. **Alerting**: Set up Grafana alerts for anomaly detection

## Troubleshooting

### If InfluxDB shows no data:
```bash
# Check if collector is running
python influx_collector.py

# Check if Sock Shop is running
docker ps | findstr docker-compose

# Restart InfluxDB if needed
cd influx-stack
docker-compose restart influxdb
```

### If Grafana can't connect to InfluxDB:
1. Check data source configuration
2. Verify InfluxDB is accessible: http://localhost:8086
3. Check token: phca-token-12345
4. Restart Grafana: `docker-compose restart grafana`

## Current Data Status
- **Records in DB**: 224 (as of checkpoint)
- **Time Range**: Last ~60 minutes
- **Collection Interval**: 5 seconds
- **All Services**: ✅ Monitored and collecting data