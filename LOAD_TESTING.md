# 🚀 Load Testing Guide

## Quick Start - Generate High Load NOW

Since Locust has threading issues, use the direct load generator:

### 1. Generate High Load (Recommended)

```bash
python3 generate_load.py
```

This will:
- Spawn **30 concurrent workers** (simulating 30 users)
- Each worker makes **1000 requests**
- Total: **30,000 requests**
- Shows real-time statistics

### 2. View Metrics in Real-Time

Open a **second terminal** and run:

```bash
python3 view_docker_metrics.py
```

This shows:
- CPU and memory usage per service
- Network I/O
- Request rates
- Updates every 5 seconds

---

## Configuration

Edit `generate_load.py` to adjust load:

```python
NUM_WORKERS = 30              # Number of concurrent users
REQUESTS_PER_WORKER = 1000    # Requests per user
DELAY_BETWEEN_REQUESTS = 0.5  # Seconds between requests
```

### Load Profiles

**Light Load (Testing):**
```python
NUM_WORKERS = 5
REQUESTS_PER_WORKER = 100
DELAY_BETWEEN_REQUESTS = 1.0
```

**Medium Load (Default):**
```python
NUM_WORKERS = 30
REQUESTS_PER_WORKER = 1000
DELAY_BETWEEN_REQUESTS = 0.5
```

**Heavy Load (Stress Test):**
```python
NUM_WORKERS = 100
REQUESTS_PER_WORKER = 5000
DELAY_BETWEEN_REQUESTS = 0.1
```

---

## What the Load Generator Does

The script simulates real user behavior:

1. **Browse homepage** - `GET /`
2. **View products** - `GET /api/products/{id}`
3. **Get recommendations** - `GET /api/recommendations?productIds={id}`
4. **View cart** - `GET /api/cart`
5. **Add to cart** - `POST /api/cart`

Each worker randomly performs these actions with realistic delays.

---

## Troubleshooting

### Frontend Not Accessible

```bash
# Check if frontend is running
docker ps | grep frontend

# Check frontend logs
docker logs frontend-proxy --tail 50
```

### No Metrics Showing

```bash
# Verify services are running
docker ps

# Check if metrics collector is running
docker ps | grep metrics-collector

# Restart metrics collector if needed
docker restart metrics-collector
```

### Load Generator Errors

If you see connection errors:
1. Make sure frontend is accessible: `curl http://localhost:8080/`
2. Check Docker containers are healthy: `docker ps`
3. Reduce load by lowering `NUM_WORKERS`

---

## Alternative: Use Locust (If Working)

If Locust is stable, you can use it:

1. Find Locust port:
   ```bash
   docker port load-generator
   ```

2. Open in browser:
   ```
   http://localhost:<port>
   ```

3. Configure:
   - Users: 30
   - Spawn rate: 5
   - Host: `http://frontend-proxy:8080`

4. Click "Start Swarming"

**Note:** Locust has threading issues and may crash mid-test. The Python script is more reliable.

---

## Expected Results

When load is running, you should see:

### In `generate_load.py`:
```
Total Requests: 5000
Success: 4950
Errors: 50
RPS: 125.3 req/s
Success Rate: 99.0%
```

### In `view_docker_metrics.py`:
```
SERVICE              CPU    MEMORY     MEM %      NET IN      NET OUT
frontend            45.2%   256.3 MB    3.2%     15.2 MB      8.4 MB
cart                32.1%   128.5 MB    1.6%      8.1 MB      4.2 MB
checkout            28.5%   145.2 MB    1.8%      6.3 MB      3.1 MB
```

---

## Tips

1. **Run both scripts simultaneously** - One generates load, one shows metrics
2. **Start metrics viewer first** - So you can see the baseline before load
3. **Use Ctrl+C to stop** - Both scripts handle interruption gracefully
4. **Adjust load gradually** - Start with low load and increase
5. **Monitor system resources** - Use `htop` to watch overall system load

---

## Summary

**Best workflow:**

```bash
# Terminal 1: Start metrics viewer
python3 view_docker_metrics.py

# Terminal 2: Generate load
python3 generate_load.py
```

This bypasses Locust's issues and gives you reliable, high-volume load testing! 🎉
