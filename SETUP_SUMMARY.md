# Real-Time ML Training Data Stream - Setup Summary

## ✅ What Has Been Created

### 1. Enhanced Metrics Collector (`src/metrics-collector/app.py`)
- **30+ comprehensive metrics** per service
- Collects from 12 microservices every 5 seconds
- Outputs structured JSON to stdout
- Enhanced with:
  - Separate disk read/write metrics
  - Separate network receive/transmit metrics
  - Mean latency alongside percentiles
  - Success rate calculation
  - GC pause time tracking
  - Request size metrics
  - 4 derived ML features (efficiency, throughput, etc.)

### 2. Real-Time Streaming Script (`realtime_ml_stream.py`)
- Streams metrics from Docker container in real-time
- Clean JSON output (one record per line)
- Features:
  - Service filtering
  - File output support
  - Pretty print mode for debugging
  - Statistics tracking
  - Sample output display

### 3. Convenience Startup Script (`start_ml_stream.sh`)
- Checks if required services are running
- Auto-starts metrics collector if needed
- Simple command-line interface
- Handles all common use cases

### 4. Documentation
- **ML_TRAINING_DATA.md**: Complete guide with 200+ lines
- **QUICKSTART_ML_STREAM.md**: Get started in 3 steps
- **SETUP_SUMMARY.md**: This file
- Updated **src/metrics-collector/README.md**

## 📊 Metrics Structure

Each JSON record contains:

```json
{
  // Identification (2 fields)
  "timestamp": "2024-10-12T18:27:45.123Z",
  "service": "cart",
  
  // Performance Metrics (7 fields)
  "rps": 120.4,
  "latency_p50_ms": 28.5,
  "latency_p95_ms": 42.1,
  "latency_p99_ms": 89.3,
  "latency_mean_ms": 31.2,
  "error_rate": 0.12,
  "success_rate": 99.88,
  
  // Resource Utilization (9 fields)
  "cpu_percent": 57.8,
  "memory_mb": 243.2,
  "memory_utilization_percent": 48.6,
  "disk_read_mb_per_sec": 0.8,
  "disk_write_mb_per_sec": 0.4,
  "disk_io_mb_per_sec": 1.2,
  "network_receive_mb_per_sec": 3.2,
  "network_transmit_mb_per_sec": 2.2,
  "network_io_mb_per_sec": 5.4,
  
  // Application Metrics (8 fields)
  "active_connections": 15,
  "queue_depth": 3,
  "response_size_kb": 2.8,
  "request_size_kb": 1.2,
  "thread_count": 12,
  "heap_usage_mb": 180.5,
  "gc_collections_per_sec": 0.8,
  "gc_pause_time_ms": 2.1,
  
  // Scaling Context (3 fields)
  "replica_count": 2,
  "target_cpu_utilization": 70.0,
  "target_memory_utilization": 70.0,
  
  // Derived ML Features (4 fields)
  "requests_per_connection": 8.03,
  "avg_response_time_ms": 31.2,
  "throughput_mb_per_sec": 0.33,
  "resource_efficiency_score": 1.89
}
```

**Total: 33 fields per record**

## 🚀 How to Use

### Basic Usage

```bash
# 1. Start all services
docker-compose up -d

# 2. Stream metrics to console
./start_ml_stream.sh

# 3. Save to file
./start_ml_stream.sh -o logs/training_data.jsonl

# 4. Filter by service
./start_ml_stream.sh -s cart -o logs/cart_metrics.jsonl
```

### Advanced Usage

```bash
# Show sample output format
python3 realtime_ml_stream.py --sample

# Pretty print for debugging
python3 realtime_ml_stream.py --pretty

# Read from stdin (for piping)
docker logs -f metrics-collector | python3 realtime_ml_stream.py --stdin

# Multiple filters and options
python3 realtime_ml_stream.py -s frontend -o logs/frontend.jsonl
```

### Data Collection Workflow

```bash
# Scenario 1: Low load
./start_ml_stream.sh -o logs/low_load_$(date +%Y%m%d).jsonl
# Run for 2 hours

# Scenario 2: Medium load (increase in Locust)
./start_ml_stream.sh -o logs/medium_load_$(date +%Y%m%d).jsonl
# Run for 2 hours

# Scenario 3: High load
./start_ml_stream.sh -o logs/high_load_$(date +%Y%m%d).jsonl
# Run for 2 hours

# Scenario 4: Spike patterns
./start_ml_stream.sh -o logs/spike_load_$(date +%Y%m%d).jsonl
# Run for 2 hours
```

## 📈 Data Analysis

```bash
# Analyze collected data
python3 analyze_metrics.py logs/training_data.jsonl

# Export for ML frameworks (CSV format)
python3 analyze_metrics.py logs/training_data.jsonl --export-ml logs/ml_ready.csv

# Analyze specific service
python3 analyze_metrics.py logs/training_data.jsonl --service cart
```

## 🎯 ML Training Features

### Input Features (X)
- **Performance**: RPS, latency percentiles, error rates
- **Resources**: CPU, memory, disk I/O, network I/O
- **Application**: connections, queue depth, threads, GC
- **Derived**: efficiency scores, throughput

### Target Variables (Y)
- **Replica count**: Current scaling state
- **Scale decisions**: Up/down/no-change
- **Future resource needs**: Predicted requirements

### Recommended Models
- **Time-Series**: LSTM, GRU for sequential patterns
- **Regression**: XGBoost, Random Forest for replica prediction
- **Classification**: Gradient Boosting for scale decisions
- **RL**: For optimal scaling policies

## 🔧 Configuration

### Metrics Collector

Edit `docker-compose.yml`:

```yaml
metrics-collector:
  environment:
    - PROMETHEUS_URL=http://prometheus:9090
    - COLLECTION_INTERVAL=5  # seconds between collections
```

### Services Monitored

All 12 microservices:
- cart
- checkout
- frontend
- product-catalog
- recommendation
- payment
- shipping
- currency
- email
- ad
- accounting
- fraud-detection

## 🛠️ Troubleshooting

### Metrics collector not running?

```bash
# Check status
docker ps | grep metrics-collector

# Start it
docker-compose up -d metrics-collector

# Check logs
docker logs metrics-collector
```

### No metrics appearing?

```bash
# Verify Prometheus is running
curl http://localhost:9090/-/ready

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Restart collector
docker-compose restart metrics-collector
```

### Services not instrumented?

```bash
# Check all services are running
docker-compose ps

# Start missing services
docker-compose up -d
```

## 📁 File Structure

```
opentelemetry-demo/
├── realtime_ml_stream.py          # Main streaming script
├── start_ml_stream.sh             # Convenience startup script
├── analyze_metrics.py             # Data analysis tool
├── ML_TRAINING_DATA.md            # Complete documentation
├── QUICKSTART_ML_STREAM.md        # Quick start guide
├── SETUP_SUMMARY.md               # This file
├── logs/                          # Output directory
│   └── training_data.jsonl        # Collected metrics
└── src/
    └── metrics-collector/         # Metrics collector service
        ├── app.py                 # Enhanced collector (30+ metrics)
        ├── stream_logs.py         # Alternative streaming tool
        ├── Dockerfile             # Container definition
        ├── requirements.txt       # Python dependencies
        └── README.md              # Service documentation
```

## ✨ Key Features

### Real-Time Streaming
- ✅ Live metrics as they're collected
- ✅ No buffering delays
- ✅ Immediate feedback

### Clean JSON Format
- ✅ One record per line (JSONL)
- ✅ Consistent structure
- ✅ Easy to parse

### Service-Aware
- ✅ Collects from all microservices
- ✅ Service filtering support
- ✅ Per-service analysis

### ML-Optimized
- ✅ 30+ comprehensive metrics
- ✅ Derived features included
- ✅ Structured for training

### Production-Ready
- ✅ Error handling
- ✅ Resource efficient
- ✅ Configurable intervals
- ✅ Docker-based deployment

## 🎓 Best Practices

### Data Collection
1. **Diverse scenarios**: Collect under various load patterns
2. **Sufficient duration**: 2-4 hours minimum per scenario
3. **Realistic load**: Use production-like traffic
4. **Label datasets**: Use descriptive filenames

### Feature Engineering
1. **Temporal features**: Add time-based features
2. **Rolling windows**: Calculate moving averages
3. **Normalization**: Scale features appropriately
4. **Feature selection**: Use correlation analysis

### Model Training
1. **Time-based split**: Don't use random splitting
2. **Cross-validation**: Use time-series CV
3. **Evaluation**: Focus on precision/recall
4. **Online learning**: Consider incremental updates

## 📞 Next Steps

1. ✅ **Setup Complete** - All files created
2. 🔄 **Start Services** - `docker-compose up -d`
3. 📊 **Start Streaming** - `./start_ml_stream.sh -o logs/training_data.jsonl`
4. 🚀 **Generate Load** - Use Locust at http://localhost:8089
5. ⏱️ **Collect Data** - Run for 2-4 hours per scenario
6. 📈 **Analyze** - `python3 analyze_metrics.py logs/training_data.jsonl`
7. 🤖 **Train Model** - Use your preferred ML framework
8. 🎯 **Deploy** - Integrate with autoscaling system

## 📚 Documentation Links

- **Quick Start**: [QUICKSTART_ML_STREAM.md](QUICKSTART_ML_STREAM.md)
- **Complete Guide**: [ML_TRAINING_DATA.md](ML_TRAINING_DATA.md)
- **Collector Details**: [src/metrics-collector/README.md](src/metrics-collector/README.md)

---

**Ready to start collecting ML training data!** 🚀
