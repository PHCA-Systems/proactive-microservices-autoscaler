# 📊 How to View Real-Time Metrics

## 🎯 The Solution

Use the **Docker-based metrics viewer** which shows **REAL** resource usage and Locust traffic:

```bash
python3 view_docker_metrics.py
```

This updates **every 5 seconds** and shows:
- ✅ **Real CPU usage** from Docker
- ✅ **Real memory usage** from Docker  
- ✅ **Network I/O** from Docker
- ✅ **Locust traffic stats** (RPS, latency, users)
- ✅ **All 12 microservices**
- ✅ **Color-coded** (🟢 green = good, 🟡 yellow = warning, 🔴 red = alert)

---

## 🚀 Quick Start

### 1. Make sure Locust is generating traffic

Open http://localhost:32822 and start load:
- Users: 50
- Spawn rate: 10
- Click "Start swarming"

### 2. Run the viewer

```bash
python3 view_docker_metrics.py
```

That's it! You'll see real-time metrics updating every 5 seconds.

---

## 📊 What You'll See

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🚀 REAL-TIME METRICS DASHBOARD                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Last Update: 2025-10-12 22:35:45
Updates: 25 | Refresh: 5s | Press Ctrl+C to stop

📊 LOAD GENERATOR (LOCUST)
────────────────────────────────────────────────────────────────────────────────
  Active Users: 50
  Total RPS: 125.4 req/s
  Latency P50: 36 ms
  Latency P95: 120 ms
  Failure Rate: 2.15%

💻 MICROSERVICES RESOURCE USAGE
────────────────────────────────────────────────────────────────────────────────

SERVICE                 CPU      MEMORY    MEM %       NET IN      NET OUT
────────────────────────────────────────────────────────────────────────────────
cart                   45.2%    156.3 MB   31.3%      2.5 MB      1.8 MB
checkout               32.1%    128.5 MB   25.7%      1.2 MB      0.9 MB
frontend               68.5%    245.2 MB   49.0%      5.3 MB      4.1 MB
...
```

---

## 🆚 Comparison: Old vs New Viewer

### ❌ Old Viewer (`view_metrics.py`)
- Shows zeros because Prometheus isn't configured for service metrics
- Requires complex Prometheus queries
- Needs services to export metrics properly

### ✅ New Viewer (`view_docker_metrics.py`)
- Shows **REAL** resource usage from Docker
- Works immediately, no configuration needed
- Shows actual CPU, memory, network usage
- Includes Locust traffic statistics
- Updates every 5 seconds as requested

---

## 🎨 Features

### Real-Time Updates
- ⏱️ **5-second refresh** (as requested)
- 📊 **Live Locust stats** (RPS, latency, users, failures)
- 💻 **Docker resource usage** (CPU, memory, network)

### Color Coding
- 🟢 **Green** = Healthy (< 60% usage)
- 🟡 **Yellow** = Warning (60-80% usage)
- 🔴 **Red** = Alert (> 80% usage)

### Comprehensive View
- ✅ All 12 microservices
- ✅ Infrastructure services (Prometheus, Grafana, etc.)
- ✅ Network I/O statistics
- ✅ Memory usage in MB and %

---

## 💡 Pro Tips

### Generate More Load
In Locust UI (http://localhost:32822):
- Increase users to 100-200
- Watch CPU and memory increase in real-time
- Monitor latency changes

### Focus on Specific Metrics
- **High CPU** = Service is processing requests
- **High Memory** = Service might need scaling
- **High Latency** = Service is overloaded
- **High Failure Rate** = Service errors

### Save Metrics for ML Training
While viewing metrics, in another terminal:
```bash
./start_ml_stream.sh -o logs/training_data.jsonl
```

This saves the detailed JSON metrics for ML model training.

---

## 🔧 Troubleshooting

### Locust stats not showing?
```bash
# Check if Locust is running
docker ps | grep load-generator

# Get Locust URL
./show_urls.sh

# Open and start load generation
```

### Services showing N/A?
```bash
# Check if services are running
docker ps

# Restart if needed
docker compose restart
```

### Viewer not updating?
- Make sure Docker is running
- Check that containers are active: `docker ps`
- Verify you have permissions: `docker stats` should work

---

## 📝 Summary

**Use this command for real-time metrics:**
```bash
python3 view_docker_metrics.py
```

**Features:**
- ✅ Updates every 5 seconds
- ✅ Shows real Docker resource usage
- ✅ Includes Locust traffic stats
- ✅ Color-coded for easy monitoring
- ✅ Works immediately, no setup needed

**Perfect for:**
- Monitoring load testing
- Watching resource usage
- Identifying bottlenecks
- Understanding service behavior

---

**Enjoy your real-time metrics dashboard! 🎉**
