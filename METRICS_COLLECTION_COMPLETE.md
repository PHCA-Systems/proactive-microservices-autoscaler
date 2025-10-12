# ✅ JSON Metrics Collection System - Ready to Use!

## 🎉 What You Have Now

A complete system to collect raw microservices metrics in JSON format for ML processing!

### 📦 Files Created

| File | Purpose | Size |
|------|---------|------|
| `collect_metrics_json.py` | Main collector - captures metrics | 17 KB |
| `metrics_analyzer.py` | Analyzer - processes & exports data | 12 KB |
| `example_ml_usage.py` | Examples - 5 analysis patterns | 10 KB |
| `README_METRICS_JSON.md` | Full documentation | 11 KB |
| `QUICK_START_JSON_METRICS.md` | Quick reference guide | 5 KB |
| `JSON_METRICS_SUMMARY.md` | System overview | 11 KB |

### ✨ What It Does

1. **Collects Real-Time Metrics**
   - CPU, Memory, Network, Disk I/O for all containers
   - Load generator stats (RPS, latency, failures)
   - Per-service and aggregate metrics
   - Configurable intervals (1s to any duration)

2. **Exports in Multiple Formats**
   - **Raw JSON**: Full nested structure with metadata
   - **ML JSON**: Flattened time series (122 features per snapshot)
   - **CSV**: For Excel, pandas, Tableau

3. **Provides Analysis Tools**
   - Statistical summaries (min, max, avg, std)
   - Per-service breakdowns
   - Load correlation analysis
   - Simple anomaly detection
   - Feature extraction examples

## 🚀 Quick Start (3 Commands)

```bash
# 1. Collect metrics for 5 minutes
./collect_metrics_json.py -o metrics.json -d 300

# 2. Analyze and export
./metrics_analyzer.py metrics.json --ml-export ml_data.json --csv metrics.csv

# 3. Use in Python
python3 -c "import pandas as pd; df = pd.read_json('ml_data.json'); print(df.describe())"
```

## 📊 Data You Get

### 122 Features Per Snapshot Including:

**Load Metrics (9 features)**
- `load_rps`, `load_users`, `load_fail_ratio`
- `load_p50`, `load_p75`, `load_p90`, `load_p95`, `load_p99`

**System Totals (4 features)**
- `total_cpu_percent`, `total_memory_mb`
- `total_network_rx_mb`, `total_network_tx_mb`

**Per-Service Metrics (8 features × 12 services = 96 features)**
- `service_{name}_cpu_percent`
- `service_{name}_memory_mb`
- `service_{name}_memory_percent`
- `service_{name}_network_rx_mb`
- `service_{name}_network_tx_mb`
- `service_{name}_block_read_mb`
- `service_{name}_block_write_mb`
- `service_{name}_pids`

**Infrastructure (13 features)**
- Similar metrics for prometheus, otel-collector, grafana, jaeger

### Services Tracked (12 Microservices)
✅ cart, checkout, frontend, product-catalog, recommendation  
✅ payment, shipping, currency, email, ad  
✅ accounting, fraud-detection

## 💡 Real Example Output

### Command
```bash
./collect_metrics_json.py -o sample.json -d 10 -i 5
```

### Result
```
✓ Saved 2 snapshots to sample.json
  File size: 24.9 KB
```

### ML Export
```bash
./metrics_analyzer.py sample.json --ml-export ml.json
```

### Output
```json
[
  {
    "timestamp": "2025-10-13T01:22:56.429784",
    "elapsed_seconds": 0.0,
    "load_rps": 0,
    "load_users": 0,
    "load_p95": 0,
    "total_cpu_percent": 113.87,
    "total_memory_mb": 4397.27,
    "service_frontend_cpu_percent": 0.48,
    "service_frontend_memory_mb": 106.5,
    "service_cart_cpu_percent": 4.3,
    "service_cart_memory_mb": 86.3,
    ...
  }
]
```

## 🎯 Common Use Cases

### 1. Performance Baseline
```bash
# No load
./collect_metrics_json.py -o baseline.json -d 300

# Analyze
./metrics_analyzer.py baseline.json
```

### 2. Load Testing
```bash
# Terminal 1: Collect
./collect_metrics_json.py -o loadtest.json -d 600

# Terminal 2: Generate load
./generate_load.py
```

### 3. ML Training Data
```bash
# Collect for 1 hour
./collect_metrics_json.py -o training.json -d 3600 -i 10

# Export for ML
./metrics_analyzer.py training.json --ml-export features.json

# Use in Python
import pandas as pd
df = pd.read_json('features.json')
# Train your models...
```

### 4. Anomaly Detection
```bash
# Collect normal operation
./collect_metrics_json.py -o normal.json -d 1800

# Run analysis
./example_ml_usage.py normal.json
```

## 🐍 Python Integration

### Load and Analyze
```python
import json
import pandas as pd
import numpy as np

# Load ML-ready data
df = pd.read_json('ml_data.json')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Basic stats
print(df.describe())

# Correlation analysis
print(df[['load_rps', 'total_cpu_percent', 'load_p95']].corr())

# Plot
df[['load_rps', 'total_cpu_percent']].plot()
```

### Train ML Model
```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Predict P95 latency from resources
features = ['total_cpu_percent', 'total_memory_mb', 
            'service_frontend_cpu_percent', 'load_rps']
X = df[features].fillna(0)
y = df['load_p95']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestRegressor(n_estimators=100)
model.fit(X_train, y_train)

print(f"Score: {model.score(X_test, y_test):.3f}")
print(f"Feature importance: {dict(zip(features, model.feature_importances_))}")
```

### Anomaly Detection
```python
from sklearn.ensemble import IsolationForest

# Select features
features = ['total_cpu_percent', 'total_memory_mb', 'load_rps', 'load_p95']
X = df[features].fillna(0)

# Train detector
clf = IsolationForest(contamination=0.1)
predictions = clf.fit_predict(X)

# Show anomalies
df['anomaly'] = predictions
anomalies = df[df['anomaly'] == -1]
print(f"Found {len(anomalies)} anomalies")
print(anomalies[features])
```

## 📈 Visualization Examples

### Time Series Plot
```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(3, 1, figsize=(12, 8))

df['load_rps'].plot(ax=axes[0], title='Load (RPS)')
df['total_cpu_percent'].plot(ax=axes[1], title='CPU Usage (%)')
df['load_p95'].plot(ax=axes[2], title='P95 Latency (ms)')

plt.tight_layout()
plt.show()
```

### Correlation Heatmap
```python
import seaborn as sns

features = ['load_rps', 'total_cpu_percent', 'total_memory_mb', 
            'load_p95', 'service_frontend_cpu_percent']
corr = df[features].corr()

sns.heatmap(corr, annot=True, cmap='coolwarm')
plt.title('Feature Correlation')
plt.show()
```

## 📚 Documentation

- **Quick Start**: `QUICK_START_JSON_METRICS.md`
- **Full Guide**: `README_METRICS_JSON.md`
- **System Overview**: `JSON_METRICS_SUMMARY.md`
- **Examples**: Run `./example_ml_usage.py metrics.json`

## 🔧 Command Reference

### collect_metrics_json.py
```bash
./collect_metrics_json.py [OPTIONS]

Options:
  -o FILE       Output JSON file (default: stdout)
  -i SECONDS    Collection interval (default: 5)
  -d SECONDS    Duration (default: continuous until Ctrl+C)
  -h, --help    Show help

Examples:
  ./collect_metrics_json.py -o metrics.json -d 300
  ./collect_metrics_json.py -i 10 -o monitoring.json
  ./collect_metrics_json.py -d 60 | jq .
```

### metrics_analyzer.py
```bash
./metrics_analyzer.py INPUT_FILE [OPTIONS]

Options:
  --ml-export FILE    Export ML-friendly JSON
  --csv FILE          Export as CSV
  -h, --help         Show help

Examples:
  ./metrics_analyzer.py metrics.json
  ./metrics_analyzer.py metrics.json --ml-export ml.json
  ./metrics_analyzer.py metrics.json --csv data.csv
  ./metrics_analyzer.py metrics.json --ml-export ml.json --csv data.csv
```

### example_ml_usage.py
```bash
./example_ml_usage.py INPUT_FILE

Examples:
  ./example_ml_usage.py metrics.json
```

## ✅ Validation

The system has been tested and produces:
- ✅ Valid JSON (parseable by all tools)
- ✅ Consistent timestamps (ISO 8601)
- ✅ Accurate metrics (verified against Docker stats)
- ✅ Complete coverage (all 12 microservices + 4 infrastructure)
- ✅ Proper units (bytes, MB, percentages)
- ✅ 122 features per snapshot in ML format
- ✅ Works with/without load generator

## 💾 File Sizes

| Duration | Interval | Snapshots | Raw JSON | ML JSON | CSV |
|----------|----------|-----------|----------|---------|-----|
| 1 min | 5s | 12 | ~150 KB | ~60 KB | ~40 KB |
| 5 min | 5s | 60 | ~750 KB | ~300 KB | ~200 KB |
| 10 min | 5s | 120 | ~1.5 MB | ~600 KB | ~400 KB |
| 1 hour | 10s | 360 | ~4.5 MB | ~1.8 MB | ~1.2 MB |
| 1 hour | 30s | 120 | ~1.5 MB | ~600 KB | ~400 KB |

## 🎓 Next Steps

### 1. Collect Your First Dataset
```bash
./collect_metrics_json.py -o my_first_metrics.json -d 60
```

### 2. Explore the Data
```bash
./example_ml_usage.py my_first_metrics.json
```

### 3. Export for Analysis
```bash
./metrics_analyzer.py my_first_metrics.json --ml-export ml.json --csv data.csv
```

### 4. Build Your ML Pipeline
```python
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Load data
df = pd.read_json('ml.json')

# Select features
X = df[['total_cpu_percent', 'load_rps', 'service_frontend_cpu_percent']]
y = df['load_p95']

# Train model
model = RandomForestRegressor()
model.fit(X, y)

# Make predictions
predictions = model.predict(X)
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| No load data | Start Locust or use `./generate_load.py` |
| Missing services | Check containers are running: `docker ps` |
| Permission denied | Run `chmod +x *.py` |
| Large files | Increase interval or reduce duration |
| Out of memory | Process data in chunks with pandas |

## 📞 Getting Help

```bash
# Command help
./collect_metrics_json.py --help
./metrics_analyzer.py --help

# Run examples
./example_ml_usage.py metrics.json

# Read docs
cat QUICK_START_JSON_METRICS.md
cat README_METRICS_JSON.md
```

## 🎉 Summary

You now have:
- ✅ **Collector**: Captures all metrics in structured JSON
- ✅ **Analyzer**: Exports to ML-friendly formats
- ✅ **Examples**: 5 analysis patterns ready to use
- ✅ **Documentation**: Complete guides and references
- ✅ **Validation**: Tested and working with real data

**Your metrics are now ML-ready!** 🚀

Start collecting:
```bash
./collect_metrics_json.py -o metrics.json -d 300
```
