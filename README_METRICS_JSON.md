# JSON Metrics Collection for ML

This guide explains how to collect raw metrics data in JSON format for machine learning analysis.

## Overview

The metrics collection system captures:
- **Docker container metrics**: CPU, memory, network I/O, block I/O, PIDs
- **Load generator stats**: RPS, user count, response time percentiles, failure rates
- **Service-level metrics**: Individual microservices and infrastructure components
- **Time-series data**: Continuous snapshots at configurable intervals

## Quick Start

### 1. Collect Metrics

```bash
# Collect for 5 minutes and save to file
./collect_metrics_json.py -o metrics.json -d 300

# Collect continuously with 10-second intervals
./collect_metrics_json.py -i 10 -o metrics.json

# Collect for 1 hour during load test
./collect_metrics_json.py -o load_test_metrics.json -d 3600 -i 5
```

### 2. Analyze Collected Data

```bash
# Show summary statistics
./metrics_analyzer.py metrics.json

# Export for ML (flattened time series)
./metrics_analyzer.py metrics.json --ml-export ml_data.json

# Export as CSV for pandas/Excel
./metrics_analyzer.py metrics.json --csv metrics.csv

# Do everything
./metrics_analyzer.py metrics.json --ml-export ml_data.json --csv metrics.csv
```

### 3. Generate Load While Collecting

```bash
# Terminal 1: Start metrics collection
./collect_metrics_json.py -o test_metrics.json -d 600

# Terminal 2: Generate load
./generate_load.py
```

## JSON Data Structure

### Raw Collection Format

```json
{
  "metadata": {
    "collection_start": "2024-10-13T01:17:00.123456",
    "collection_end": "2024-10-13T01:22:00.123456",
    "total_duration_seconds": 300.0,
    "collection_interval_seconds": 5,
    "total_snapshots": 60,
    "services_monitored": {
      "microservices": ["cart", "checkout", "frontend", ...],
      "infrastructure": ["prometheus", "otel-collector", "grafana", "jaeger"]
    }
  },
  "snapshots": [
    {
      "timestamp": "2024-10-13T01:17:00.123456",
      "elapsed_seconds": 0.0,
      "collection_interval": 5,
      "load_generator": {
        "available": true,
        "port": 32852,
        "total_rps": 58.5,
        "fail_ratio": 0.0,
        "user_count": 30,
        "response_time_percentiles": {
          "p50": 45.0,
          "p75": 67.0,
          "p90": 89.0,
          "p95": 102.0,
          "p99": 145.0
        },
        "endpoints": [
          {
            "name": "/api/products/{id}",
            "method": "GET",
            "num_requests": 1234,
            "num_failures": 0,
            "avg_response_time": 45.6,
            "min_response_time": 12.3,
            "max_response_time": 234.5,
            "current_rps": 5.2,
            "median_response_time": 43.2,
            "ninety_fifth_response_time": 102.3
          }
        ]
      },
      "services": {
        "microservices": {
          "cart": {
            "container_id": "abc123...",
            "cpu_percent": 4.3,
            "memory": {
              "usage_bytes": 90505011,
              "limit_bytes": 167772160,
              "usage_mb": 86.3,
              "limit_mb": 160.0,
              "percent": 54.0
            },
            "network": {
              "rx_bytes": 17825792,
              "tx_bytes": 63865856,
              "rx_mb": 17.0,
              "tx_mb": 60.9
            },
            "block_io": {
              "read_bytes": 0,
              "write_bytes": 0,
              "read_mb": 0.0,
              "write_mb": 0.0
            },
            "pids": 12
          }
        },
        "infrastructure": {
          "prometheus": { /* same structure */ },
          "otel-collector": { /* same structure */ }
        }
      },
      "summary": {
        "total_services": 16,
        "microservices_count": 12,
        "infrastructure_count": 4,
        "total_cpu_percent": 61.4,
        "total_memory_mb": 1560.3,
        "total_network_rx_mb": 215.2,
        "total_network_tx_mb": 523.4
      }
    }
  ]
}
```

### ML-Friendly Export Format

The `--ml-export` option flattens the data into a time series suitable for ML:

```json
[
  {
    "timestamp": "2024-10-13T01:17:00.123456",
    "elapsed_seconds": 0.0,
    "load_rps": 58.5,
    "load_users": 30,
    "load_fail_ratio": 0.0,
    "load_p50": 45.0,
    "load_p75": 67.0,
    "load_p90": 89.0,
    "load_p95": 102.0,
    "load_p99": 145.0,
    "total_cpu_percent": 61.4,
    "total_memory_mb": 1560.3,
    "total_network_rx_mb": 215.2,
    "total_network_tx_mb": 523.4,
    "service_cart_cpu_percent": 4.3,
    "service_cart_memory_mb": 86.3,
    "service_cart_memory_percent": 54.0,
    "service_cart_network_rx_mb": 17.0,
    "service_cart_network_tx_mb": 60.9,
    "service_cart_block_read_mb": 0.0,
    "service_cart_block_write_mb": 0.0,
    "service_cart_pids": 12,
    "service_frontend_cpu_percent": 34.1,
    "service_frontend_memory_mb": 127.4,
    ...
  }
]
```

## Command Reference

### collect_metrics_json.py

```bash
./collect_metrics_json.py [OPTIONS]

Options:
  -o, --output FILE      Output JSON file (default: stdout)
  -i, --interval SEC     Collection interval in seconds (default: 5)
  -d, --duration SEC     Total duration in seconds (default: continuous)
  -h, --help            Show help message
```

### metrics_analyzer.py

```bash
./metrics_analyzer.py INPUT_FILE [OPTIONS]

Arguments:
  INPUT_FILE            JSON file from collect_metrics_json.py

Options:
  --ml-export FILE      Export ML-friendly JSON
  --csv FILE            Export as CSV
  -h, --help           Show help message
```

## Use Cases

### 1. Performance Testing

```bash
# Collect baseline metrics (no load)
./collect_metrics_json.py -o baseline.json -d 300

# Collect under load
./collect_metrics_json.py -o load_test.json -d 600 &
./generate_load.py

# Analyze and compare
./metrics_analyzer.py baseline.json
./metrics_analyzer.py load_test.json
```

### 2. ML Model Training

```bash
# Collect training data over extended period
./collect_metrics_json.py -o training_data.json -d 7200 -i 10

# Export for ML framework
./metrics_analyzer.py training_data.json --ml-export ml_features.json

# Use in Python
import json
import pandas as pd

with open('ml_features.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)
# Now use df for training models
```

### 3. Anomaly Detection

```bash
# Collect normal operation data
./collect_metrics_json.py -o normal.json -d 1800

# Collect during incident
./collect_metrics_json.py -o incident.json -d 600

# Export both for comparison
./metrics_analyzer.py normal.json --ml-export normal_ml.json
./metrics_analyzer.py incident.json --ml-export incident_ml.json
```

### 4. Capacity Planning

```bash
# Collect at different load levels
./collect_metrics_json.py -o low_load.json -d 600 &
# (run low load test)

./collect_metrics_json.py -o medium_load.json -d 600 &
# (run medium load test)

./collect_metrics_json.py -o high_load.json -d 600 &
# (run high load test)

# Analyze each
./metrics_analyzer.py low_load.json --csv low.csv
./metrics_analyzer.py medium_load.json --csv medium.csv
./metrics_analyzer.py high_load.json --csv high.csv
```

## Data Fields Reference

### Load Generator Fields
- `load_rps`: Requests per second
- `load_users`: Number of concurrent users
- `load_fail_ratio`: Failure ratio (0.0 to 1.0)
- `load_p50/p75/p90/p95/p99`: Response time percentiles in milliseconds

### Service Fields (per service)
- `service_{name}_cpu_percent`: CPU usage percentage
- `service_{name}_memory_mb`: Memory usage in MB
- `service_{name}_memory_percent`: Memory usage percentage
- `service_{name}_network_rx_mb`: Network received in MB
- `service_{name}_network_tx_mb`: Network transmitted in MB
- `service_{name}_block_read_mb`: Disk read in MB
- `service_{name}_block_write_mb`: Disk write in MB
- `service_{name}_pids`: Number of processes

### Summary Fields
- `total_cpu_percent`: Total CPU across all services
- `total_memory_mb`: Total memory across all services
- `total_network_rx_mb`: Total network received
- `total_network_tx_mb`: Total network transmitted

## Tips

1. **Collection Interval**: Use 5s for detailed analysis, 10-30s for long-term monitoring
2. **Duration**: Collect at least 5 minutes for meaningful statistics
3. **File Size**: Expect ~1-2 KB per snapshot (300 KB for 5 minutes at 5s interval)
4. **Concurrent Collection**: You can run multiple collectors with different intervals
5. **Piping**: Use `| jq .` to pretty-print JSON output to stdout

## Integration with ML Frameworks

### Pandas

```python
import json
import pandas as pd

with open('ml_features.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Now analyze
print(df.describe())
df.plot(y=['load_rps', 'total_cpu_percent'])
```

### NumPy

```python
import json
import numpy as np

with open('ml_features.json') as f:
    data = json.load(f)

# Extract specific features
cpu_data = np.array([d['total_cpu_percent'] for d in data])
memory_data = np.array([d['total_memory_mb'] for d in data])

# Analyze
print(f"CPU: mean={cpu_data.mean():.2f}, std={cpu_data.std():.2f}")
print(f"Memory: mean={memory_data.mean():.2f}, std={memory_data.std():.2f}")
```

### Scikit-learn

```python
import json
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

# Load data
with open('ml_features.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)

# Select features for anomaly detection
features = ['total_cpu_percent', 'total_memory_mb', 
            'load_rps', 'load_p95']
X = df[features].fillna(0)

# Normalize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train anomaly detector
clf = IsolationForest(contamination=0.1)
predictions = clf.fit_predict(X_scaled)

# Add predictions to dataframe
df['anomaly'] = predictions
print(df[df['anomaly'] == -1])  # Show anomalies
```

## Troubleshooting

**No load generator data**: Make sure Locust is running or use `./generate_load.py`

**Missing services**: Services only appear if their containers are running

**Large file sizes**: Reduce collection duration or increase interval

**Memory issues**: Process data in chunks for very large collections

## See Also

- `view_docker_metrics.py` - Real-time dashboard
- `generate_load.py` - Load generator
- Docker stats documentation
- Locust API documentation
