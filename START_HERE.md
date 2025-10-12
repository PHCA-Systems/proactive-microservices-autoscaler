# 🚀 START HERE - Quick Guide

## ✅ Your System is Ready!

Everything is set up and running. Here's how to use it:

---

## 📊 Step 1: View Service URLs

```bash
./show_urls.sh
```

This shows you all the important URLs including **Locust**.

---

## 🎯 Step 2: Generate Load

**⚠️ Locust has issues - Use the Python load generator instead:**

### Quick Start (One Command):
```bash
./start_load_test.sh
```

### Manual (Two Terminals):
```bash
# Terminal 1: View metrics
python3 view_docker_metrics.py

# Terminal 2: Generate load
python3 generate_load.py
```

This generates **30 concurrent users** making **30,000 requests** total.

See **QUICK_START_LOAD.md** for details.

---

## 👀 Step 3: View Metrics (Beautiful Format)

### Option A: Compact View (All Services)
```bash
python3 view_metrics.py --compact
```

Shows all services on one screen with key metrics:
- RPS (Requests per second)
- CPU usage
- Memory usage
- Latency P95
- Error rate

### Option B: Detailed View (One Service)
```bash
python3 view_metrics.py -s cart
```

Shows detailed metrics for a specific service with:
- ⚡ Performance metrics
- 💻 Resource utilization
- 🔧 Application metrics
- 📊 Scaling context

### Option C: Auto-rotating View
```bash
python3 view_metrics.py
```

Shows detailed view, rotating through services.

---

## 💾 Step 4: Save Data for ML Training

```bash
./start_ml_stream.sh -o logs/training_data.jsonl
```

This saves all metrics to a file for later ML model training.

**Let it run for 2-4 hours** to collect good training data!

---

## 📈 Quick Commands Reference

```bash
# Show all URLs
./show_urls.sh

# View metrics (compact - all services)
python3 view_metrics.py --compact

# View metrics (detailed - specific service)
python3 view_metrics.py -s cart

# Save metrics to file
./start_ml_stream.sh -o logs/training_data.jsonl

# Analyze saved data
python3 analyze_metrics.py logs/training_data.jsonl

# Check running services
docker ps

# View raw logs
docker logs metrics-collector --tail 20
```

---

## 🌐 Important URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Locust** | http://localhost:32822 | Generate load |
| **Grafana** | http://localhost:32802 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics queries |
| **Jaeger** | http://localhost:32806 | Distributed tracing |
| **Demo App** | http://localhost:8080 | E-commerce demo |

---

## 🎨 Metrics Viewer Features

The `view_metrics.py` script shows metrics with:

✅ **Color coding:**
- 🟢 Green = Good (low CPU, low latency, low errors)
- 🟡 Yellow = Warning (medium values)
- 🔴 Red = Alert (high values)

✅ **Real-time updates** every second

✅ **Clean formatting** with units (%, MB, ms, /s)

✅ **Service filtering** to focus on specific services

---

## 💡 Pro Tips

1. **Start with Locust** - Generate load first to see real metrics
2. **Use compact view** - See all services at once
3. **Filter by service** - Focus on specific microservices
4. **Save to file** - Collect data for ML training
5. **Let it run** - 2-4 hours of data is ideal for training

---

## 🆘 Troubleshooting

### Can't access Locust?
```bash
# Check if it's running
docker ps | grep load-generator

# Get the port
./show_urls.sh

# Restart if needed
docker compose restart load-generator
```

### Metrics not updating?
```bash
# Check metrics collector
docker logs metrics-collector --tail 20

# Restart if needed
docker compose restart metrics-collector
```

### No services running?
```bash
# Start all services
docker compose up -d

# Wait 30 seconds for startup
sleep 30

# Check status
docker ps
```

---

## 📚 Full Documentation

- **[README_ML_STREAM.md](README_ML_STREAM.md)** - Complete overview
- **[QUICKSTART_ML_STREAM.md](QUICKSTART_ML_STREAM.md)** - Quick start guide
- **[ML_TRAINING_DATA.md](ML_TRAINING_DATA.md)** - Detailed ML guide
- **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Technical details

---

## 🎯 Your Next Steps

1. ✅ **Open Locust:** http://localhost:32822
2. ✅ **Start load:** 50 users, spawn rate 10
3. ✅ **View metrics:** `python3 view_metrics.py --compact`
4. ✅ **Save data:** `./start_ml_stream.sh -o logs/training_data.jsonl`
5. ✅ **Let it run:** 2-4 hours for good training data

---

**You're all set! Enjoy collecting ML training data! 🎉**
