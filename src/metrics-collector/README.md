# Metrics Collector for ML Autoscaling Training

This service collects comprehensive real-time metrics from all microservices for training machine learning models for autoscaling decisions.

## Features

- **Real-time data collection** every 5 seconds (configurable)
- **Comprehensive metrics** including performance, resource usage, and business metrics
- **Structured JSON output** optimized for ML training
- **Service-aware** - collects data from all microservices
- **Prometheus integration** - leverages existing monitoring infrastructure

## Metrics Collected

Each log entry contains the following metrics for optimal ML training:

### Core Performance Metrics
- `timestamp`: ISO 8601 timestamp
- `service`: Service name (cart, checkout, frontend, etc.)
- `rps`: Requests per second
- `latency_p50_ms`: 50th percentile latency in milliseconds
- `latency_p95_ms`: 95th percentile latency in milliseconds  
- `latency_p99_ms`: 99th percentile latency in milliseconds
- `error_rate`: Error rate percentage

### Resource Utilization
- `cpu_percent`: CPU usage percentage
- `memory_mb`: Memory usage in MB
- `memory_utilization_percent`: Memory utilization as percentage of limit
- `disk_io_mb_per_sec`: Disk I/O in MB/second
- `network_io_mb_per_sec`: Network I/O in MB/second

### Application Metrics
- `active_connections`: Number of active connections
- `queue_depth`: Request queue depth
- `response_size_kb`: Average response size in KB
- `thread_count`: Number of threads
- `heap_usage_mb`: Heap memory usage in MB
- `gc_collections_per_sec`: Garbage collection rate

### Scaling Context
- `replica_count`: Current number of replicas
- `target_cpu_utilization`: Target CPU for autoscaling (70%)

## Usage

### Quick Start

1. **Start the entire demo environment:**
   ```bash
   docker-compose up -d
   ```

2. **Start metrics collection:**
   ```bash
   # On Linux/Mac
   ./start_metrics_collection.sh
   
   # On Windows
   start_metrics_collection.bat
   ```

3. **Generate load** (in another terminal):
   ```bash
   # Access Locust at http://localhost:8089
   # Configure load testing to generate realistic traffic
   ```

### Manual Usage

1. **Build and start the metrics collector:**
   ```bash
   docker-compose build metrics-collector
   docker-compose up -d metrics-collector
   ```

2. **Stream metrics to console:**
   ```bash
   python src/metrics-collector/stream_logs.py
   ```

3. **Save metrics to file:**
   ```bash
   python src/metrics-collector/stream_logs.py --output training_data.jsonl
   ```

4. **Filter by specific service:**
   ```bash
   python src/metrics-collector/stream_logs.py --service cart --output cart_metrics.jsonl
   ```

### Configuration

Environment variables:
- `PROMETHEUS_URL`: Prometheus endpoint (default: http://prometheus:9090)
- `COLLECTION_INTERVAL`: Collection interval in seconds (default: 5)

## Sample Output

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "service": "cart",
  "rps": 120.4,
  "cpu_percent": 57.8,
  "memory_mb": 243.2,
  "latency_p95_ms": 42.1,
  "latency_p50_ms": 28.5,
  "latency_p99_ms": 89.3,
  "error_rate": 0.12,
  "active_connections": 15,
  "queue_depth": 3,
  "response_size_kb": 2.8,
  "disk_io_mb_per_sec": 1.2,
  "network_io_mb_per_sec": 5.4,
  "replica_count": 2,
  "target_cpu_utilization": 70.0,
  "memory_utilization_percent": 48.6,
  "gc_collections_per_sec": 0.8,
  "thread_count": 12,
  "heap_usage_mb": 180.5
}
```

## ML Training Considerations

The metrics are designed to provide optimal features for autoscaling ML models:

### Input Features
- Current resource utilization (CPU, memory, network, disk)
- Performance metrics (latency percentiles, RPS, error rate)
- Application-specific metrics (connections, queue depth, GC rate)
- Temporal context (timestamp for time-series analysis)

### Target Variables
- `replica_count`: Current scaling state
- Future resource needs can be derived from trends

### Data Quality
- 5-second intervals provide good temporal resolution
- Comprehensive metrics reduce feature engineering needs
- Structured JSON format enables easy ingestion
- Service-specific data allows per-service model training

## Integration with Existing Tools

- **Grafana**: Visualize metrics trends and patterns
- **Locust**: Generate realistic load patterns for training data
- **Prometheus**: Source of truth for all metrics
- **OpenTelemetry**: Leverages existing instrumentation

## Troubleshooting

1. **No metrics appearing:**
   - Check if Prometheus is running: `docker-compose ps prometheus`
   - Verify services are instrumented: `curl http://localhost:9090/api/v1/targets`

2. **Missing service metrics:**
   - Ensure services are running: `docker-compose ps`
   - Check service instrumentation in Prometheus targets

3. **High resource usage:**
   - Increase collection interval: `COLLECTION_INTERVAL=10`
   - Reduce number of services monitored

## Next Steps

1. **Collect training data** for several hours/days under various load conditions
2. **Feature engineering** - add derived metrics, moving averages, trends
3. **Model training** - use time-series or regression models for autoscaling decisions
4. **Integration** - connect trained models to Kubernetes HPA or custom autoscaler