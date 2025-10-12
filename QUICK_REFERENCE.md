# 🚀 Quick Reference Card

## 📊 View Real-Time Metrics (5-Second Updates)

```bash
python3 view_docker_metrics.py
```

**Shows:**
- ✅ Locust traffic stats (RPS, latency, users)
- ✅ Docker resource usage (CPU, memory, network)
- ✅ All 12 microservices
- ✅ Color-coded (🟢 🟡 🔴)
- ✅ Updates every 5 seconds

---

## 🌐 Important URLs

```bash
# Show all URLs
./show_urls.sh
```

| Service | URL | Purpose |
|---------|-----|---------|
| **Locust** | http://localhost:32822 | Generate load |
| **Demo App** | http://localhost:8080 | E-commerce site |
| **Grafana** | http://localhost:32802 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics |

---

## 🎯 Generate Load

1. **Open:** http://localhost:32822
2. **Configure:**
   - Users: `50`
   - Spawn rate: `10`
3. **Click:** "Start swarming"

---

## 💾 Save Data for ML Training

```bash
# Save metrics to file
./start_ml_stream.sh -o logs/training_data.jsonl

# Analyze saved data
python3 analyze_metrics.py logs/training_data.jsonl
```

---

## 🔧 Common Commands

```bash
# View metrics (5s updates)
python3 view_docker_metrics.py

# Show URLs
./show_urls.sh

# Check running services
docker ps

# Restart services
docker compose restart

# View logs
docker logs metrics-collector --tail 20

# Stop all services
docker compose down
```

---

## 📚 Documentation Files

- **[START_HERE.md](START_HERE.md)** - Complete quick start
- **[FIXED_VIEWER.md](FIXED_VIEWER.md)** - Bug fix details
- **[VIEW_METRICS_GUIDE.md](VIEW_METRICS_GUIDE.md)** - Viewer guide
- **[ML_TRAINING_DATA.md](ML_TRAINING_DATA.md)** - ML training guide

---

## 🎨 Color Coding

- 🟢 **Green** = Healthy (< 60% usage)
- 🟡 **Yellow** = Warning (60-80% usage)
- 🔴 **Red** = Alert (> 80% usage)

---

## 💡 Pro Tips

1. **Start Locust first** - Generate load to see real metrics
2. **Watch the dashboard** - Metrics update every 5 seconds
3. **Save data** - Use `start_ml_stream.sh` for ML training
4. **Increase load** - Try 100-200 users in Locust
5. **Monitor bottlenecks** - Watch for red values

---

## 🆘 Quick Troubleshooting

### Metrics showing zeros?
→ Start load generation in Locust

### Viewer crashing?
→ Fixed! Just run `python3 view_docker_metrics.py`

### Can't access Locust?
→ Run `./show_urls.sh` to get the correct URL

### Services not running?
→ Run `docker compose up -d`

---

**Everything you need on one page! 🎉**
