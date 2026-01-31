# 🔧 Fix Grafana "No Data" Issue

## ✅ Data Confirmed in InfluxDB
Your InfluxDB has **14 services** with **fresh data** (last updated: 2026-01-30 04:41:46)

## 🎯 Step-by-Step Grafana Fix

### Step 1: Access Grafana
1. Go to: http://localhost:3000
2. Login: **admin** / **admin**
3. If prompted to change password, you can skip or set a new one

### Step 2: Check Data Source
1. Click the **gear icon** (⚙️) in left sidebar → **Data Sources**
2. You should see **"InfluxDB"** listed
3. Click on **"InfluxDB"**
4. Scroll down and click **"Save & Test"**
5. Should show: ✅ **"Data source is working"**

### Step 3: Test in Explore
1. Click **"Explore"** (compass icon 🧭) in left sidebar
2. Make sure **"InfluxDB"** is selected in the dropdown at top
3. **IMPORTANT**: Set time range to **"Last 1 hour"** (top right)
4. Paste this exact query:

```flux
from(bucket: "microservices")
  |> range(start: -30m)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

5. Click **"Run Query"**
6. You should see a graph with 14 different colored lines (one per service)

### Step 4: If Still No Data - Try This Simple Query
```flux
from(bucket: "microservices")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> limit(n: 100)
```

### Step 5: Create a Dashboard
1. Click **"+"** → **"Dashboard"**
2. Click **"Add new panel"**
3. Select **"InfluxDB"** data source
4. Use this query for a nice CPU overview:

```flux
from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

5. Set **Panel Title**: "CPU Usage by Service"
6. Click **"Apply"**

## 🚨 Common Issues & Fixes

### Issue 1: "No data points" message
**Fix**: Change time range to "Last 6 hours" or "Last 1 hour"

### Issue 2: Query syntax error
**Fix**: Make sure you're using **Flux** language, not **InfluxQL**

### Issue 3: Wrong data source selected
**Fix**: Ensure "InfluxDB" is selected in the dropdown (not "-- Grafana --")

### Issue 4: Data source connection failed
**Fix**: 
1. Go to Data Sources → InfluxDB
2. Check URL: `http://influxdb:8086`
3. Check Token: `phca-token-12345`
4. Check Organization: `phca`
5. Check Default Bucket: `microservices`

## 📊 Ready-to-Use Grafana Queries

### CPU Usage (Multi-Service)
```flux
from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "cpu_percent")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

### Memory Usage (MB)
```flux
from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "memory_usage_bytes")
  |> group(columns: ["service_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

### Network I/O (MB/s)
```flux
from(bucket: "microservices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "container_metrics")
  |> filter(fn: (r) => r["_field"] == "network_rx_bytes" or r["_field"] == "network_tx_bytes")
  |> group(columns: ["service_name", "_field"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> derivative(unit: 1s, nonNegative: true)
  |> map(fn: (r) => ({ r with _value: r._value / 1024.0 / 1024.0 }))
```

## ✅ Expected Results
After following these steps, you should see:
- **14 services** in your graphs: carts, catalogue, orders, payment, user, etc.
- **Real-time data** updating every 5 seconds
- **Multiple metrics**: CPU, memory, network, disk I/O
- **Time-series graphs** showing trends over time

## 🆘 Still Having Issues?
Run this command to verify everything is working:
```bash
python test_grafana_connection.py
```

This will confirm data exists and provide the exact query to test in Grafana.