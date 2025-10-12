# ML Training Data Collection for Autoscaling

Real-time metrics streaming system for training machine learning models for microservices autoscaling.

## 🎯 Overview

This system collects comprehensive, real-time metrics from all microservices in structured JSON format, optimized for ML model training. Each metric record contains 30+ features covering performance, resource utilization, and application behavior.

## 📊 Metrics Collected

### Performance Metrics
- **RPS** (Requests Per Second): Current request rate
- **Latency Percentiles**: P50, P95, P99, and mean latency in milliseconds
- **Error Rate**: Percentage of failed requests (5xx errors)
- **Success Rate**: Percentage of successful requests

### Resource Utilization
- **CPU**: CPU usage percentage
- **Memory**: Memory usage in MB and utilization percentage
- **Disk I/O**: Read/write rates in MB/sec (separate and total)
- **Network I/O**: Receive/transmit rates in MB/sec (separate and total)

### Application Metrics
- **Active Connections**: Number of concurrent connections
- **Queue Depth**: Request queue size
- **Request/Response Sizes**: Average sizes in KB
- **Thread Count**: Number of active threads
- **Heap Usage**: JVM/runtime heap memory in MB
- **GC Metrics**: Garbage collection rate and pause times

### Scaling Context
- **Replica Count**: Current number of service replicas
- **Target Utilization**: CPU and memory targets for autoscaling

### Derived Metrics (ML Features)
- **Requests Per Connection**: Efficiency metric
- **Throughput**: MB/sec data throughput
- **Resource Efficiency Score**: Requests per unit of resource

## 🚀 Quick Start

### 1. Start the System

```bash
# Start all services including metrics collector
docker-compose up -d

# Or start specific services
docker-compose up -d prometheus otel-collector metrics-collector
```

### 2. Stream Metrics in Real-Time

```bash
# Stream to console
./start_ml_stream.sh

# Save to file for training
./start_ml_stream.sh -o logs/training_data.jsonl

# Filter specific service
./start_ml_stream.sh -s cart -o logs/cart_metrics.jsonl

# Pretty print for debugging
./start_ml_stream.sh --pretty
```

### 3. Generate Load (Optional)

```bash
# Start load generator
docker-compose up -d load-generator

# Access Locust UI at http://localhost:8089
# Configure users and spawn rate to generate realistic traffic
```

## 📝 Sample Output

Each line is a complete JSON record:

```json
{
  "timestamp": "2024-10-12T18:27:45.123Z",
  "service": "cart",
  "rps": 120.4,
  "latency_p50_ms": 28.5,
  "latency_p95_ms": 42.1,
  "latency_p99_ms": 89.3,
  "latency_mean_ms": 31.2,
  "error_rate": 0.12,
  "success_rate": 99.88,
  "cpu_percent": 57.8,
  "memory_mb": 243.2,
  "memory_utilization_percent": 48.6,
  "disk_read_mb_per_sec": 0.8,
  "disk_write_mb_per_sec": 0.4,
  "disk_io_mb_per_sec": 1.2,
  "network_receive_mb_per_sec": 3.2,
  "network_transmit_mb_per_sec": 2.2,
  "network_io_mb_per_sec": 5.4,
  "active_connections": 15,
  "queue_depth": 3,
  "response_size_kb": 2.8,
  "request_size_kb": 1.2,
  "thread_count": 12,
  "heap_usage_mb": 180.5,
  "gc_collections_per_sec": 0.8,
  "gc_pause_time_ms": 2.1,
  "replica_count": 2,
  "target_cpu_utilization": 70.0,
  "target_memory_utilization": 70.0,
  "requests_per_connection": 8.03,
  "avg_response_time_ms": 31.2,
  "throughput_mb_per_sec": 0.33,
  "resource_efficiency_score": 1.89
}
```

## 🔧 Advanced Usage

### Direct Python Script

```bash
# Show sample output format
python3 realtime_ml_stream.py --sample

# Stream from Docker container
python3 realtime_ml_stream.py -o training_data.jsonl

# Read from stdin (for piping)
docker logs -f metrics-collector | python3 realtime_ml_stream.py --stdin

# Filter and save
python3 realtime_ml_stream.py -s frontend -o frontend_metrics.jsonl
```

### Configuration

Environment variables for metrics collector (in `docker-compose.yml`):

```yaml
environment:
  - PROMETHEUS_URL=http://prometheus:9090
  - COLLECTION_INTERVAL=5  # seconds between collections
```

### Services Monitored

- `cart` - Shopping cart service
- `checkout` - Checkout service
- `frontend` - Frontend service
- `product-catalog` - Product catalog service
- `recommendation` - Recommendation service
- `payment` - Payment service
- `shipping` - Shipping service
- `currency` - Currency conversion service
- `email` - Email service
- `ad` - Advertisement service
- `accounting` - Accounting service
- `fraud-detection` - Fraud detection service

## 🤖 ML Training Workflow

### 1. Data Collection Phase

Collect data under various load conditions:

```bash
# Low load scenario
./start_ml_stream.sh -o logs/low_load.jsonl
# Run for 1-2 hours

# Medium load scenario
# Increase load in Locust UI
./start_ml_stream.sh -o logs/medium_load.jsonl
# Run for 1-2 hours

# High load scenario
# Further increase load
./start_ml_stream.sh -o logs/high_load.jsonl
# Run for 1-2 hours

# Spike scenario
# Create traffic spikes
./start_ml_stream.sh -o logs/spike_load.jsonl
# Run for 1-2 hours
```

### 2. Data Analysis

```bash
# Analyze collected data
python3 analyze_metrics.py logs/training_data.jsonl

# Export for ML frameworks
python3 analyze_metrics.py logs/training_data.jsonl --export-ml logs/ml_ready.csv

# Analyze specific service
python3 analyze_metrics.py logs/training_data.jsonl --service cart
```

### 3. Feature Engineering

The data includes pre-computed derived features:
- `requests_per_connection`: Load distribution efficiency
- `resource_efficiency_score`: Overall resource utilization efficiency
- `throughput_mb_per_sec`: Data throughput
- `avg_response_time_ms`: Average response time

Additional features you can derive:
- Rolling averages (5-min, 15-min windows)
- Rate of change (CPU delta, memory delta)
- Time-based features (hour of day, day of week)
- Lag features (previous values)
- Trend indicators (increasing/decreasing)

### 4. Model Training Considerations

**Input Features (X):**
- Current resource utilization (CPU, memory, network, disk)
- Performance metrics (RPS, latency percentiles, error rate)
- Application metrics (connections, queue depth, threads)
- Temporal features (time of day, trends)

**Target Variables (Y):**
- Optimal replica count (classification/regression)
- Future resource needs (time-series forecasting)
- Scale-up/scale-down decisions (binary classification)

**Recommended Models:**
- **Time-Series**: LSTM, GRU for sequential patterns
- **Regression**: XGBoost, Random Forest for replica prediction
- **Classification**: Gradient Boosting for scale decisions
- **Reinforcement Learning**: For optimal scaling policies

## 📈 Monitoring & Visualization

### Grafana Dashboards

Access Grafana at http://localhost:3000 (admin/admin) to visualize:
- Real-time metrics trends
- Service health status
- Resource utilization patterns
- Performance correlations

### Prometheus Queries

Access Prometheus at http://localhost:9090 for custom queries:

```promql
# Service RPS
rate(http_requests_total{service_name="cart"}[1m])

# CPU usage
rate(process_cpu_seconds_total{service_name="cart"}[1m]) * 100

# Memory usage
process_resident_memory_bytes{service_name="cart"} / 1024 / 1024

# Latency P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service_name="cart"}[1m])) * 1000
```

## 🔍 Troubleshooting

### No Metrics Appearing

```bash
# Check if metrics collector is running
docker-compose ps metrics-collector

# Check logs
docker logs metrics-collector

# Restart if needed
docker-compose restart metrics-collector
```

### Missing Service Data

```bash
# Check if services are running
docker-compose ps

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify service instrumentation
docker logs <service-name>
```

### High Resource Usage

```bash
# Increase collection interval
# Edit docker-compose.yml:
environment:
  - COLLECTION_INTERVAL=10  # Increase from 5 to 10 seconds

# Restart metrics collector
docker-compose restart metrics-collector
```

### Data Quality Issues

```bash
# Check for missing values
python3 analyze_metrics.py logs/training_data.jsonl

# Validate JSON format
jq empty logs/training_data.jsonl

# Count records per service
jq -r '.service' logs/training_data.jsonl | sort | uniq -c
```

## 📚 File Structure

```
opentelemetry-demo/
├── realtime_ml_stream.py          # Main streaming script
├── start_ml_stream.sh             # Convenience startup script
├── ML_TRAINING_DATA.md            # This documentation
├── analyze_metrics.py             # Data analysis tool
├── logs/                          # Output directory for metrics
│   └── training_data.jsonl        # Collected metrics
└── src/
    └── metrics-collector/         # Metrics collector service
        ├── app.py                 # Collector implementation
        ├── Dockerfile             # Container definition
        └── requirements.txt       # Python dependencies
```

## 🎓 Best Practices

### Data Collection
1. **Diverse Scenarios**: Collect data under various load patterns
2. **Sufficient Duration**: Run for at least 2-4 hours per scenario
3. **Realistic Load**: Use production-like traffic patterns
4. **Label Data**: Track which scenario each dataset represents

### Feature Engineering
1. **Temporal Features**: Add time-based features for patterns
2. **Rolling Windows**: Calculate moving averages for trends
3. **Normalization**: Scale features appropriately for your model
4. **Feature Selection**: Use correlation analysis to identify key features

### Model Training
1. **Train/Test Split**: Use time-based splitting (not random)
2. **Cross-Validation**: Use time-series cross-validation
3. **Evaluation Metrics**: Focus on precision/recall for scaling decisions
4. **Online Learning**: Consider incremental learning for adaptation

### Production Deployment
1. **Model Versioning**: Track model versions and performance
2. **A/B Testing**: Compare ML-based vs rule-based autoscaling
3. **Monitoring**: Track model predictions vs actual needs
4. **Fallback**: Have rule-based fallback for model failures

## 🔗 Integration Examples

### Kubernetes HPA

```python
# Example: Use model predictions for HPA
from kubernetes import client, config

def scale_deployment(service_name, predicted_replicas):
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    
    deployment = apps_v1.read_namespaced_deployment(
        name=service_name,
        namespace="default"
    )
    
    deployment.spec.replicas = predicted_replicas
    apps_v1.patch_namespaced_deployment(
        name=service_name,
        namespace="default",
        body=deployment
    )
```

### Custom Autoscaler

```python
# Example: Real-time autoscaling with ML model
import json
import joblib

model = joblib.load('autoscaler_model.pkl')

def predict_scaling_action(metrics):
    features = extract_features(metrics)
    prediction = model.predict([features])
    return prediction[0]  # scale_up, scale_down, or no_action

# Stream and predict
for line in stream_metrics():
    metrics = json.loads(line)
    action = predict_scaling_action(metrics)
    if action != 'no_action':
        execute_scaling(metrics['service'], action)
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs: `docker logs metrics-collector`
3. Verify Prometheus connectivity: `curl http://localhost:9090/-/ready`
4. Check service instrumentation in Prometheus targets

## 📄 License

This is part of the OpenTelemetry Demo project.
