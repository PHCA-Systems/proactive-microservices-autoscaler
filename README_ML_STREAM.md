# 🤖 Real-Time ML Training Data Stream

**Comprehensive metrics collection system for training autoscaling ML models**

## 🎯 What This Does

Streams **30+ real-time metrics** from all microservices in clean JSON format, optimized for training machine learning models for intelligent autoscaling decisions.

```json
{"timestamp":"2024-10-12T18:27:45.123Z","service":"cart","rps":120.4,"cpu_percent":57.8,"memory_mb":243.2,"latency_p95_ms":42.1,...}
```

## ⚡ Quick Start (3 Commands)

```bash
# 1. Start services
docker-compose up -d

# 2. Stream metrics to file
./start_ml_stream.sh -o logs/training_data.jsonl

# 3. Generate load (optional)
open http://localhost:8089  # Locust UI
```

**That's it!** Metrics are now streaming to `logs/training_data.jsonl`

## 📊 What You Get

### 33 Metrics Per Service, Every 5 Seconds

**Performance** (7 metrics)
- RPS, latency (P50/P95/P99/mean), error rate, success rate

**Resources** (9 metrics)
- CPU, memory, disk I/O (read/write), network I/O (receive/transmit)

**Application** (8 metrics)
- Connections, queue depth, request/response sizes, threads, heap, GC

**Scaling** (3 metrics)
- Replica count, CPU/memory targets

**Derived** (4 metrics)
- Efficiency score, throughput, requests per connection

**Services Monitored** (12 total)
- cart, checkout, frontend, product-catalog, recommendation, payment, shipping, currency, email, ad, accounting, fraud-detection

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICKSTART_ML_STREAM.md](QUICKSTART_ML_STREAM.md)** | Get started in 3 steps |
| **[ML_TRAINING_DATA.md](ML_TRAINING_DATA.md)** | Complete guide (200+ lines) |
| **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** | What was created & how to use |
| **[src/metrics-collector/README.md](src/metrics-collector/README.md)** | Technical details |

## 🚀 Common Commands

```bash
# Verify setup
./verify_ml_setup.sh

# Stream to console
./start_ml_stream.sh

# Save to file
./start_ml_stream.sh -o logs/training_data.jsonl

# Filter specific service
./start_ml_stream.sh -s cart -o logs/cart_metrics.jsonl

# Pretty print (debugging)
./start_ml_stream.sh --pretty

# Show sample output
python3 realtime_ml_stream.py --sample

# Analyze collected data
python3 analyze_metrics.py logs/training_data.jsonl

# Export for ML (CSV)
python3 analyze_metrics.py logs/training_data.jsonl --export-ml logs/ml_ready.csv
```

## 🎓 ML Training Workflow

### 1. Collect Data (2-4 hours per scenario)

```bash
# Low load
./start_ml_stream.sh -o logs/low_load.jsonl

# Medium load (increase in Locust)
./start_ml_stream.sh -o logs/medium_load.jsonl

# High load
./start_ml_stream.sh -o logs/high_load.jsonl

# Spike patterns
./start_ml_stream.sh -o logs/spike_load.jsonl
```

### 2. Analyze Data

```bash
python3 analyze_metrics.py logs/training_data.jsonl
python3 analyze_metrics.py logs/training_data.jsonl --export-ml logs/ml_ready.csv
```

### 3. Train Model

Use your preferred ML framework with:
- **Input (X)**: Performance + resource + application metrics
- **Target (Y)**: Replica count / scale decisions / future needs
- **Models**: LSTM, XGBoost, Random Forest, RL

### 4. Deploy

Integrate predictions with Kubernetes HPA or custom autoscaler

## 🔧 Configuration

Edit `docker-compose.yml`:

```yaml
metrics-collector:
  environment:
    - COLLECTION_INTERVAL=5  # Change collection frequency
```

## 🛠️ Troubleshooting

```bash
# Check services
docker-compose ps

# Check metrics collector logs
docker logs metrics-collector

# Restart metrics collector
docker-compose restart metrics-collector

# Verify Prometheus
curl http://localhost:9090/-/ready

# Run verification
./verify_ml_setup.sh
```

## 📁 Files Created

```
├── realtime_ml_stream.py          # Main streaming script
├── start_ml_stream.sh             # Convenience wrapper
├── verify_ml_setup.sh             # Setup verification
├── analyze_metrics.py             # Data analysis
├── ML_TRAINING_DATA.md            # Complete guide
├── QUICKSTART_ML_STREAM.md        # Quick start
├── SETUP_SUMMARY.md               # Setup summary
├── README_ML_STREAM.md            # This file
└── src/metrics-collector/
    └── app.py                     # Enhanced collector (30+ metrics)
```

## ✨ Features

✅ **Real-time streaming** - No buffering, immediate output  
✅ **Clean JSON** - One record per line (JSONL format)  
✅ **30+ metrics** - Comprehensive feature set  
✅ **Service-aware** - All 12 microservices  
✅ **ML-optimized** - Derived features included  
✅ **Production-ready** - Error handling, configurable  
✅ **Easy to use** - Simple scripts, clear docs  

## 🎯 Use Cases

- Train autoscaling ML models
- Predict optimal replica counts
- Forecast resource needs
- Detect scaling patterns
- Optimize resource allocation
- Research autoscaling strategies

## 📞 Need Help?

1. Run `./verify_ml_setup.sh` to check setup
2. See [QUICKSTART_ML_STREAM.md](QUICKSTART_ML_STREAM.md) for basics
3. See [ML_TRAINING_DATA.md](ML_TRAINING_DATA.md) for details
4. Check `docker logs metrics-collector` for issues

## 🚦 Status

✅ **Setup Complete** - All components ready  
✅ **Tested** - Scripts verified working  
✅ **Documented** - Comprehensive guides included  

**Ready to collect ML training data!** 🎉

---

*Part of the OpenTelemetry Demo project - Enhanced for ML autoscaling research*
