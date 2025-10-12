# 🔧 Locust Issues - BETTER SOLUTION

## ⚠️ Problem: Locust Has Persistent Threading Issues

Locust keeps crashing with gevent/threading errors and "connection refused" issues.

## ✅ BETTER SOLUTION: Direct Python Load Generator

**Use the reliable Python load generator instead of Locust:**

```bash
./start_load_test.sh
```

Or manually:
```bash
# Terminal 1: View metrics
python3 view_docker_metrics.py

# Terminal 2: Generate load
python3 generate_load.py
```

See **QUICK_START_LOAD.md** for full details.

---

## 🌐 New Locust URL

**Open this in your browser:**

```
http://localhost:32851
```

*(Port changed after restart - this is normal)*

---

## 🚀 How to Start Load Generation

### 1. Open Locust
http://localhost:32851

### 2. Click "New Test" or "Edit"

### 3. Configure:
- **Number of users:** `50`
- **Spawn rate:** `10`
- **Host:** `http://frontend-proxy:8080` (use this instead of frontend)

### 4. Click "Start Swarming"

---

## 💡 Why It Was Stuck

**Issue:** Locust had a threading/gevent assertion error
**Cause:** Internal state corruption
**Fix:** Restart the container

---

## 🎯 Quick Commands

```bash
# Get current Locust URL
./show_urls.sh

# Restart Locust if stuck again
docker compose restart load-generator

# Check Locust logs
docker logs load-generator --tail 20

# View metrics while load is running
python3 view_docker_metrics.py
```

---

## 📊 Expected Behavior After Fix

Once you start the load:
- Status changes from "SPAWNING" to "RUNNING"
- Users count increases (0 → 50)
- RPS shows traffic (e.g., 125.4 req/s)
- Statistics table fills with data
- Metrics viewer shows real traffic

---

## 🔄 If It Gets Stuck Again

```bash
# Stop Locust
docker compose stop load-generator

# Start it fresh
docker compose up -d load-generator

# Wait 10 seconds
sleep 10

# Get new URL
./show_urls.sh

# Open in browser and configure
```

---

## ✨ Alternative: Use Frontend Proxy Directly

If Locust continues having issues, you can test the app directly:

1. **Open:** http://localhost:8080
2. **Browse the site** manually
3. **Metrics will still be collected** from your browsing

---

## 📝 Summary

**Fixed:** Restarted Locust container
**New URL:** http://localhost:32851
**Host to use:** `http://frontend-proxy:8080`

**Next steps:**
1. Open http://localhost:32851
2. Configure: 30 users, spawn rate 1 (or higher for faster ramp)
3. Host: `http://frontend-proxy:8080`
4. Click "Start Swarming"
5. Run `python3 view_docker_metrics.py` to see metrics

---

**Locust is now ready to use! 🎉**
