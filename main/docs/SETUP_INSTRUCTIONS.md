# PHCA Monitoring Setup Instructions

## Quick Start (5 minutes)

### 1. Start Sock Shop (if not already running)
```bash
cd microservices-demo/deploy/docker-compose
docker-compose up -d
```

### 2. Start Monitoring Stack
```bash
cd monitoring-stack
docker-compose up -d
```

### 3. Verify Setup
```bash
# Check if all services are running
docker ps | grep -E "(phca_|microservices-demo)"

# Test metrics collection
python setup_monitoring.py
```

### 4. Run Your First Experiment
```bash
# Single pattern test (5 minutes)
python run_phca_experiment.py --pattern constant --duration 300 --users 50

# Full experiment suite (20 minutes)
python run_phca_experiment.py --pattern all --duration 300 --users 50
```

## Access Points

- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **cAdvisor Container Stats**: http://localhost:8080
- **Sock Shop Application**: http://localhost:80

## What You Get

### Metrics Collected (every 5 seconds):
- **CPU Usage**: Per-container CPU utilization percentage
- **Memory Usage**: Memory consumption and limits
- **Network I/O**: Bytes and packets sent/received
- **Disk I/O**: File system read/write rates
- **Container Count**: Number of replicas per service

### Services Monitored:
- front-end, catalogue, catalogue-db
- carts, carts-db, orders, orders-db
- shipping, queue-master, rabbitmq
- payment, user, user-db, edge-router

### Data Output:
- **CSV files**: `data/experiment_name_timestamp.csv`
- **Load test reports**: `results/experiment_name_report.html`
- **Summary statistics**: `results/experiment_name_summary.csv`

## Troubleshooting

### Prometheus Not Collecting Data
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Restart monitoring stack
cd monitoring-stack
docker-compose restart
```

### Sock Shop Not Accessible
```bash
# Check Sock Shop services
cd microservices-demo/deploy/docker-compose
docker-compose ps

# Restart if needed
docker-compose restart
```

### No Container Metrics
```bash
# Check cAdvisor
curl http://localhost:8080/metrics

# Verify Docker socket access
ls -la /var/run/docker.sock
```

## Data Analysis

### Load Data in Python
```python
import pandas as pd

# Load experiment data
df = pd.read_csv('data/your_experiment_file.csv')

# Basic analysis
print(df.groupby('service_name')['cpu_usage'].mean())
print(df.groupby('service_name')['memory_percent'].max())
```

### Key Metrics for ML
- `cpu_usage`: CPU utilization percentage
- `memory_percent`: Memory utilization percentage  
- `network_rx/tx`: Network throughput
- `fs_read/write`: Disk I/O rates

## Next Steps

1. **Collect Baseline Data**: Run experiments with different load patterns
2. **Feature Engineering**: Calculate rolling averages, detect anomalies
3. **ML Model Training**: Use collected data to train autoscaling models
4. **Real-time Integration**: Connect ML models to Kubernetes HPA

## File Structure
```
├── monitoring-stack/          # Prometheus + Grafana setup
├── data/                     # Collected metrics (CSV files)
├── results/                  # Load test reports and summaries
├── run_phca_experiment.py    # Main experiment runner
└── SETUP_INSTRUCTIONS.md     # This file
```