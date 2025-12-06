# Load Generator Integration Guide

## How LoadGenerator Works

The `LoadGenerator` class is a sophisticated load testing framework that integrates with Locust to generate HTTP load and collect comprehensive performance metrics.

### Architecture Overview

```
LoadGenerator
    ├── Locust (Load Testing Engine)
    │   ├── Master (orchestrates load)
    │   └── Workers (generate actual requests)
    ├── Statistics Collection
    │   ├── CSV output (aggregated stats)
    │   └── CSV history (time-series)
    ├── Replica Monitoring
    │   └── measure_replicas.py (background process)
    └── QoE Evaluation
        └── compute_qoe() (Quality of Experience scoring)
```

### Key Components

#### 1. **Load Generation (`generate_load()`)**
- Uses Locust in headless mode
- Generates load at specified RPS (Requests Per Second)
- Runs for specified duration
- Outputs CSV statistics

#### 2. **Distributed Load Generation (`generate_load_distributed()`)**
- Uses Locust master/worker architecture
- Scales to multiple workers for high RPS
- Better for generating >1000 RPS

#### 3. **Statistics Reading (`read_load_statistics()`)**
- Reads Locust CSV output
- Extracts latency percentiles (50%, 90%, 95%, 99%)
- Gets request rates and failure rates

#### 4. **QoE Evaluation (`eval_qoe()`)**
- Computes Quality of Experience score
- Based on latency threshold and action cost
- Formula: `(latency_threshold - actual_latency) * w_l - action * w_i`
- Negative scores indicate poor performance

#### 5. **Workload Execution (`run_workload()`)**
- Runs sequence of RPS rates
- Collects performance metrics for each
- Tracks replicas and resource utilization
- Returns comprehensive results

### Workflow

```
1. Initialize LoadGenerator
   ↓
2. Start replica monitoring (background)
   ↓
3. Generate load at RPS rate
   ↓
4. Locust executes HTTP requests
   ↓
5. Collect statistics from CSV
   ↓
6. Get deployment/replica info
   ↓
7. Get resource utilization
   ↓
8. Compute QoE score
   ↓
9. Return results
```

## Integration with Sock Shop

### File Structure

```
Autoscale/
├── loadgen/
│   ├── load_generator.py      # Main LoadGenerator class (DO NOT MODIFY)
│   ├── locustfile.py          # Locust test scenarios
│   └── example_usage.py       # Usage examples
├── utils/
│   └── kube.py                # Kubernetes/Docker utilities
├── evaluation/
│   └── eval_utils/
│       └── measure_replicas.py # Replica monitoring
└── logs/
    └── scratch/                # CSV output directory
```

### Dependencies

The LoadGenerator requires:
- **Locust**: HTTP load testing framework
- **Pandas**: Data analysis (reading CSV)
- **NumPy**: Numerical operations
- **utils.kube**: Kubernetes/Docker utilities (provided)

### Usage Example

```python
from loadgen.load_generator import LoadGenerator

# Initialize
lg = LoadGenerator(
    host='http://localhost',  # Sock Shop URL
    locustfile='loadgen/locustfile.py',
    duration=25
)

# Generate load
lg.generate_load(rps=10)

# Get statistics
stats = lg.read_load_statistics(rps=10)
print(stats)
# Output:
# {
#   'Average Latency': 45.2,
#   '95p Latency': 120.5,
#   'Output RPS': 9.8,
#   ...
# }
```

## Integration Points

### 1. **With Metrics Collector**

The LoadGenerator works alongside `collect_autoscaling_metrics.py`:

- **LoadGenerator**: Generates load, measures performance (latency, RPS)
- **Metrics Collector**: Measures resources (CPU, memory) and application metrics

**Combined Workflow**:
```python
# Start metrics collector in background
# Run load generator
lg.generate_load(rps=50)
# Metrics collector shows CPU/memory increase
# LoadGenerator shows latency/RPS metrics
```

### 2. **With Docker Compose**

The `utils/kube.py` module adapts to Docker Compose:
- Uses `docker-compose ps` to get deployments
- Uses `docker stats` to get resource utilization
- Works seamlessly without Kubernetes

### 3. **With Kubernetes** (if deployed)

If you deploy to Kubernetes:
- `utils/kube.py` uses `kubectl` commands
- Gets deployment replicas from Kubernetes API
- Gets pod statistics from Kubernetes metrics

## Locustfile Configuration

The `locustfile.py` defines user behavior:

- **Browse Catalogue**: Most common (weight=3)
- **View Cart**: Common (weight=2)
- **Add to Cart**: Less common (weight=1)
- **Create Order**: Less common (weight=1)

Weights determine probability of each task.

## Output Files

### CSV Statistics (`logs/scratch/cola_lg.csv_stats.csv`)
Aggregated statistics:
- Request counts
- Latency percentiles
- Failure rates
- RPS

### CSV History (`logs/scratch/cola_lg.csv_stats_history.csv`)
Time-series data:
- Per-second metrics
- Detailed latency distribution
- Request rate over time

### Replica Counts (`service_replicas_count.json`)
JSONL format (one JSON per line):
```json
{"timestamp": "2025-12-06T15:30:00Z", "replicas": {"front-end": 1, "carts": 2}}
{"timestamp": "2025-12-06T15:30:01Z", "replicas": {"front-end": 1, "carts": 2}}
```

## QoE Scoring

The Quality of Experience (QoE) function:

```
QoE = (latency_threshold - actual_latency) * w_l - action * w_i
```

- **Positive QoE**: Good performance (latency < threshold)
- **Negative QoE**: Poor performance (latency > threshold)
- **Action cost**: Penalty for scaling actions

## Troubleshooting

### Locust not found
```bash
pip install locust
```

### CSV files not created
- Check `logs/scratch/` directory exists
- Check Locust has write permissions

### Replica monitoring not working
- Check `service_replicas_count.json` is being created
- Verify `measure_replicas.py` is running

### Docker commands failing
- Ensure Docker is running
- Check `docker-compose` is in PATH
- Verify containers are running

## Next Steps

1. **Run Example**:
   ```bash
   python loadgen/example_usage.py
   ```

2. **Customize Locustfile**:
   - Edit `loadgen/locustfile.py` to match your test scenarios

3. **Integrate with Autoscaling**:
   - Use QoE scores to trigger scaling decisions
   - Combine with metrics collector for full picture

4. **Scale Testing**:
   - Use `generate_load_distributed()` for high RPS
   - Adjust `num_workers` based on your needs

