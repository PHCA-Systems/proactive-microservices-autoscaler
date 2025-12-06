# Load Generator for Sock Shop

This module provides load generation capabilities using Locust for testing the Sock Shop microservices application.

## Overview

The `LoadGenerator` class uses Locust to generate HTTP load against the Sock Shop application, collect performance metrics, and evaluate Quality of Experience (QoE).

## Components

- **`load_generator.py`**: Main LoadGenerator class (DO NOT MODIFY)
- **`locustfile.py`**: Locust test scenarios for Sock Shop
- **`utils/kube.py`**: Utilities for getting deployment and pod statistics
- **`evaluation/eval_utils/measure_replicas.py`**: Background script to measure replica counts

## Dependencies

Install required packages:
```bash
pip install locust pandas numpy
```

## Usage

### Basic Example

```python
from loadgen.load_generator import LoadGenerator

# Initialize load generator
lg = LoadGenerator(
    host='http://localhost',  # Sock Shop front-end URL
    locustfile='loadgen/locustfile.py',
    duration=25,  # Test duration in seconds
    csv_path='logs/scratch/cola_lg',
    latency_threshold=100  # ms
)

# Generate load at 10 requests per second
lg.generate_load(rps=10)

# Read statistics
stats = lg.read_load_statistics(rps=10)
print(stats)

# Evaluate QoE
qoe, stats = lg.eval_qoe(rps=10, action=0)
print(f"QoE: {qoe}")
```

### Running a Workload Sequence

```python
# Run multiple RPS rates in sequence
rps_rates = [5, 10, 20, 50, 100]
results = lg.run_workload(rps_rates)

# Results contain performance metrics, deployments, utilization, and replicas
for result in results:
    print(f"RPS: {result['rps_rate']}")
    print(f"Latency P95: {result['perf']['95p Latency']} ms")
    print(f"Replicas: {result['replicas']}")
```

## Output Files

- **CSV Statistics**: `logs/scratch/cola_lg.csv_stats.csv` - Aggregated statistics
- **CSV History**: `logs/scratch/cola_lg.csv_stats_history.csv` - Time-series data
- **Replica Counts**: `service_replicas_count.json` - Replica measurements over time

## Integration with Metrics Collector

The LoadGenerator works alongside the metrics collector (`deploy/docker-compose/collect_autoscaling_metrics.py`):

1. **LoadGenerator**: Generates load and collects performance metrics
2. **Metrics Collector**: Collects resource metrics (CPU, memory) and application metrics

Together, they provide a complete picture of system performance under load.

## Notes

- The LoadGenerator is designed to work with both Docker Compose and Kubernetes
- For Docker Compose, it uses `docker-compose ps` and `docker stats`
- For Kubernetes, it uses `kubectl` commands
- The `measure_replicas.py` script runs in the background during load tests

