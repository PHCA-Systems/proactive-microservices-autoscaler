# Quick Start: JSON Metrics for ML

## 🚀 Collect Metrics in 3 Steps

### Step 1: Start Collecting
```bash
# Collect for 5 minutes
./collect_metrics_json.py -o metrics.json -d 300
```

### Step 2: Analyze Data
```bash
# View summary
./metrics_analyzer.py metrics.json

# Export for ML
./metrics_analyzer.py metrics.json --ml-export ml_data.json --csv metrics.csv
```

### Step 3: Use in Your ML Pipeline
```python
import json
import pandas as pd

# Load as DataFrame
df = pd.read_json('ml_data.json')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Analyze
print(df.describe())
df.plot(y=['load_rps', 'total_cpu_percent'])
```

## 📊 What Data You Get

### Raw Format (metrics.json)
```json
{
  "metadata": {
    "collection_start": "2024-10-13T01:17:00",
    "total_snapshots": 60,
    "collection_interval_seconds": 5
  },
  "snapshots": [
    {
      "timestamp": "2024-10-13T01:17:00",
      "load_generator": {
        "total_rps": 58.5,
        "user_count": 30,
        "response_time_percentiles": {
          "p50": 45, "p95": 102, "p99": 145
        }
      },
      "services": {
        "microservices": {
          "cart": {
            "cpu_percent": 4.3,
            "memory": {"usage_mb": 86.3, "percent": 54.0},
            "network": {"rx_mb": 17.0, "tx_mb": 60.9}
          }
        }
      },
      "summary": {
        "total_cpu_percent": 61.4,
        "total_memory_mb": 1560.3
      }
    }
  ]
}
```

### ML Format (ml_data.json)
```json
[
  {
    "timestamp": "2024-10-13T01:17:00",
    "load_rps": 58.5,
    "load_users": 30,
    "load_p95": 102.0,
    "total_cpu_percent": 61.4,
    "total_memory_mb": 1560.3,
    "service_cart_cpu_percent": 4.3,
    "service_cart_memory_mb": 86.3,
    "service_frontend_cpu_percent": 34.1,
    ...
  }
]
```

## 🎯 Common Use Cases

### 1. Baseline Performance
```bash
# No load
./collect_metrics_json.py -o baseline.json -d 300

# With load
./collect_metrics_json.py -o load.json -d 300 &
./generate_load.py
```

### 2. Long-term Monitoring
```bash
# Collect for 1 hour
./collect_metrics_json.py -o monitoring.json -d 3600 -i 10
```

### 3. Load Testing
```bash
# Terminal 1: Start collection
./collect_metrics_json.py -o loadtest.json -d 600

# Terminal 2: Generate load
./generate_load.py
```

### 4. Quick Analysis
```bash
# Collect and analyze
./collect_metrics_json.py -o test.json -d 60
./example_ml_usage.py test.json
```

## 📈 Available Features

### Load Metrics
- `load_rps` - Requests per second
- `load_users` - Concurrent users
- `load_p50/p75/p90/p95/p99` - Response time percentiles
- `load_fail_ratio` - Failure rate

### System Metrics
- `total_cpu_percent` - Total CPU usage
- `total_memory_mb` - Total memory usage
- `total_network_rx_mb` - Total network received
- `total_network_tx_mb` - Total network transmitted

### Per-Service Metrics (for each service)
- `service_{name}_cpu_percent`
- `service_{name}_memory_mb`
- `service_{name}_memory_percent`
- `service_{name}_network_rx_mb`
- `service_{name}_network_tx_mb`
- `service_{name}_block_read_mb`
- `service_{name}_block_write_mb`
- `service_{name}_pids`

## 🔧 Command Options

### collect_metrics_json.py
```bash
-o FILE      # Output file (default: stdout)
-i SECONDS   # Collection interval (default: 5)
-d SECONDS   # Duration (default: continuous)
```

### metrics_analyzer.py
```bash
INPUT_FILE      # JSON file to analyze
--ml-export     # Export ML-friendly JSON
--csv           # Export as CSV
```

## 💡 Tips

1. **Interval**: Use 5s for detailed analysis, 10-30s for long-term
2. **Duration**: Minimum 5 minutes for meaningful stats
3. **File Size**: ~1-2 KB per snapshot (300 KB for 5 min @ 5s)
4. **Concurrent**: Can run multiple collectors simultaneously
5. **Real-time**: Use `view_docker_metrics.py` for live dashboard

## 🐍 Python Integration

### Pandas
```python
import pandas as pd

df = pd.read_json('ml_data.json')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Analyze
print(df.describe())
print(df.corr())  # Correlation matrix

# Plot
df[['load_rps', 'total_cpu_percent']].plot()
```

### NumPy
```python
import json
import numpy as np

with open('ml_data.json') as f:
    data = json.load(f)

cpu = np.array([d['total_cpu_percent'] for d in data])
rps = np.array([d['load_rps'] for d in data])

print(f"Correlation: {np.corrcoef(cpu, rps)[0,1]:.3f}")
```

### Scikit-learn
```python
from sklearn.ensemble import RandomForestRegressor
import pandas as pd

df = pd.read_json('ml_data.json')

# Predict latency from resource usage
X = df[['total_cpu_percent', 'total_memory_mb', 'load_rps']]
y = df['load_p95']

model = RandomForestRegressor()
model.fit(X, y)

print(f"Feature importance: {model.feature_importances_}")
```

## 📚 Full Documentation

See `README_METRICS_JSON.md` for complete documentation including:
- Detailed data structure
- Advanced analysis examples
- Integration with ML frameworks
- Troubleshooting guide

## 🆘 Troubleshooting

**No load data**: Start Locust or use `./generate_load.py`

**Missing services**: Ensure containers are running (`docker ps`)

**Large files**: Reduce duration or increase interval

**Permission denied**: Run `chmod +x *.py`

## 📞 Quick Help

```bash
./collect_metrics_json.py --help
./metrics_analyzer.py --help
./example_ml_usage.py metrics.json
```
