# Quick Start: Real-Time ML Training Data Stream

## 🚀 Get Started in 3 Steps

### Step 1: Start the Services

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
docker-compose ps
```

### Step 2: Start Streaming Metrics

```bash
# Stream to console (see real-time data)
./start_ml_stream.sh

# OR save to file for training
./start_ml_stream.sh -o logs/training_data.jsonl
```

### Step 3: Generate Load (Optional)

```bash
# Start load generator
docker-compose up -d load-generator

# Open Locust UI
open http://localhost:8089

# Configure:
# - Number of users: 50-100
# - Spawn rate: 10
# - Host: http://frontend:8080
# Click "Start swarming"
```

## 📊 What You'll See

Each line is a JSON record with 30+ metrics:

```json
{
  "timestamp": "2024-10-12T18:27:45.123Z",
  "service": "cart",
  "rps": 120.4,
  "cpu_percent": 57.8,
  "memory_mb": 243.2,
  "latency_p95_ms": 42.1,
  "error_rate": 0.12,
  ...30+ more metrics
}
```

## 🎯 Common Use Cases

### Collect Training Data for 2 Hours

```bash
./start_ml_stream.sh -o logs/training_$(date +%Y%m%d_%H%M%S).jsonl
# Let it run for 2+ hours with varying load
# Press Ctrl+C when done
```

### Monitor Specific Service

```bash
./start_ml_stream.sh -s cart -o logs/cart_metrics.jsonl
```

### Debug with Pretty Print

```bash
./start_ml_stream.sh --pretty
```

## 🔍 Verify It's Working

```bash
# Check metrics collector is running
docker logs metrics-collector --tail 20

# Check file is being written
tail -f logs/training_data.jsonl

# Count records collected
wc -l logs/training_data.jsonl
```

## 📈 Analyze Collected Data

```bash
# Basic analysis
python3 analyze_metrics.py logs/training_data.jsonl

# Export for ML frameworks (CSV)
python3 analyze_metrics.py logs/training_data.jsonl --export-ml logs/ml_ready.csv
```

## 🛠️ Troubleshooting

### No metrics appearing?

```bash
# Check if services are running
docker-compose ps

# Restart metrics collector
docker-compose restart metrics-collector

# Check Prometheus
curl http://localhost:9090/-/ready
```

### Want to change collection interval?

Edit `docker-compose.yml`:
```yaml
metrics-collector:
  environment:
    - COLLECTION_INTERVAL=10  # Change from 5 to 10 seconds
```

Then restart:
```bash
docker-compose restart metrics-collector
```

## 📚 Full Documentation

- **Complete Guide**: See [ML_TRAINING_DATA.md](ML_TRAINING_DATA.md)
- **Metrics Details**: See [src/metrics-collector/README.md](src/metrics-collector/README.md)

## 💡 Tips

1. **Collect diverse scenarios**: low load, high load, spikes
2. **Run for sufficient time**: 2-4 hours per scenario minimum
3. **Label your data**: Use descriptive filenames
4. **Monitor disk space**: JSONL files can grow large

## 🎓 Next Steps

1. Collect data under various load patterns
2. Analyze with `analyze_metrics.py`
3. Feature engineering (rolling averages, trends)
4. Train your ML model
5. Deploy autoscaling based on predictions

---

**Need help?** Check the full documentation or review the logs.
