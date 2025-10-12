# 🚀 Quick Start - Generate Load NOW

Locust is having issues, so I created a **direct Python load generator** that's more reliable.

---

## ⚡ Fastest Way (One Command)

```bash
./start_load_test.sh
```

This automatically:
1. Checks frontend is accessible
2. Starts metrics viewer
3. Generates high load (30 users, 30K requests)
4. Shows real-time statistics

---

## 📊 Manual Way (Two Terminals)

### Terminal 1: View Metrics
```bash
python3 view_docker_metrics.py
```

### Terminal 2: Generate Load
```bash
python3 generate_load.py
```

---

## 🎯 What You'll See

### Load Generator Output:
```
╔══════════════════════════════════════════════════════════╗
║               HIGH-LOAD GENERATOR                        ║
╚══════════════════════════════════════════════════════════╝

Configuration:
  Workers: 30
  Requests per worker: 1000
  Total requests: 30000
  Target: http://localhost:8080

============================================================
Total Requests: 5234
Success: 5180
Errors: 54
RPS: 125.3 req/s
Success Rate: 99.0%
============================================================
```

### Metrics Viewer Output:
```
╔══════════════════════════════════════════════════════════╗
║           🚀 REAL-TIME METRICS DASHBOARD                 ║
╚══════════════════════════════════════════════════════════╝

💻 MICROSERVICES RESOURCE USAGE
────────────────────────────────────────────────────────────

SERVICE              CPU    MEMORY     MEM %      NET IN      NET OUT
frontend            45.2%   256.3 MB    3.2%     15.2 MB      8.4 MB
cart                32.1%   128.5 MB    1.6%      8.1 MB      4.2 MB
checkout            28.5%   145.2 MB    1.8%      6.3 MB      3.1 MB
product-catalog     25.3%   112.4 MB    1.4%      5.2 MB      2.8 MB
```

---

## ⚙️ Adjust Load Level

Edit `generate_load.py` (lines 19-21):

**Light Load:**
```python
NUM_WORKERS = 5
REQUESTS_PER_WORKER = 100
DELAY_BETWEEN_REQUESTS = 1.0
```

**Heavy Load:**
```python
NUM_WORKERS = 100
REQUESTS_PER_WORKER = 5000
DELAY_BETWEEN_REQUESTS = 0.1
```

---

## 🔧 Why Not Locust?

Locust has persistent threading/gevent issues causing:
- Random crashes mid-test
- "Connection refused" errors
- UI becoming unresponsive
- Workers not spawning properly

The Python script is:
- ✓ More reliable
- ✓ Easier to configure
- ✓ Shows real-time stats
- ✓ No UI needed

---

## 📝 Files Created

- **`generate_load.py`** - Direct load generator (bypasses Locust)
- **`view_docker_metrics.py`** - Real-time metrics viewer (updated)
- **`start_load_test.sh`** - One-command launcher
- **`LOAD_TESTING.md`** - Detailed documentation
- **`QUICK_START_LOAD.md`** - This file

---

## ✅ Verify It's Working

1. Run the load generator
2. Watch the request count increase
3. Open metrics viewer in another terminal
4. See CPU/memory usage spike
5. Check your metrics collector is receiving data

---

## 🎉 Ready to Go!

Just run:
```bash
./start_load_test.sh
```

Or manually:
```bash
# Terminal 1
python3 view_docker_metrics.py

# Terminal 2  
python3 generate_load.py
```

**Your metrics collector will now have plenty of data to display!** 📊
