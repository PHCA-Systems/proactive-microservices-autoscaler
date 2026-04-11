# ML-Driven Proactive Microservices Autoscaling

## Project Overview

A real-time machine learning-based autoscaling system for microservices using Kafka message broker and ensemble voting. This project enhances the Weaveworks Sock Shop microservices demo with intelligent autoscaling capabilities.

## Architecture

Three trained ML models (XGBoost, Random Forest, Logistic Regression) continuously monitor service metrics and vote on scaling decisions through a Kafka-based architecture.

```
Sock Shop Services → Prometheus → Metrics Aggregator → Kafka → 3 ML Models → Kafka → Authoritative Scaler → Decisions
```

### Key Components

1. **Metrics Aggregator Service**: Polls Prometheus every 30s and publishes feature vectors to Kafka
2. **ML Inference Services** (3): XGBoost, Random Forest, Logistic Regression models predict SLA violations
3. **Authoritative Scaling Service**: Aggregates votes and makes final scaling decisions
4. **Kafka Message Broker**: Enables real-time streaming with topics `metrics` and `model-votes`
5. **Scaling Controller**: Executes scaling decisions via Kubernetes API

## Infrastructure

### GKE Cluster Configuration
- **Cluster**: sock-shop-cluster (us-central1-a)
- **Nodes**: 3× e2-standard-4 (4 vCPU, 16 GB RAM each)
- **Total Resources**: 12 vCPUs, 48 GB RAM
- **Services**: 7 monitored (front-end, carts, orders, catalogue, user, payment, shipping)

### SLA Threshold
- **Threshold**: 35.68ms (p95 latency of front-end service)
- **Derivation**: P75 of front-end p95 latency across constant load runs
- **Polling Interval**: 30 seconds
- **Lookahead Window**: 60 seconds (2 intervals)

## Model Performance

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|-------|----------|-----------|--------|----------|---------|
| XGBoost | 99.87% | 99.74% | 100.00% | 99.87% | 99.87% |
| Random Forest | 99.87% | 99.74% | 100.00% | 99.87% | 99.87% |
| Logistic Regression | 99.74% | 99.48% | 100.00% | 99.74% | 99.74% |

All models achieve 100% recall for SLA violations (no false negatives).

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- 8GB RAM minimum

### Start Production Mode
```cmd
start-production.bat
```

### View Scaling Decisions
```cmd
docker-compose -f docker-compose.ml.yml logs -f authoritative-scaler
```

### Stop All Services
```cmd
stop-all.bat
```

## Project Structure

```
.
├── services/                       # Microservices
│   ├── metrics-aggregator/         # Polls Prometheus, publishes to Kafka
│   ├── ml-inference/               # ML model inference service
│   ├── authoritative-scaler/       # Vote aggregator & decision engine
│   └── scaling-controller/         # K8s API executor
│
├── ML-Models/                      # Trained models
│   ├── gke/                        # GKE-trained models
│   └── local/                      # Local-trained models
│
├── data/                           # Collected metrics
│   ├── gke/experiments/            # Per-pattern experiments
│   └── local/                      # Local Docker experiments
│
├── load-testing/                   # Locust load tests
├── microservices-demo/             # Sock Shop demo
└── docs/                           # Additional documentation
```

## Experimental Methodology

### Load Patterns
Four patterns from EuroSys'24 Erlang paper:
- **constant**: Flat steady-state load (50 users)
- **ramp**: Gradual increase to peak, then down (10-150 users)
- **spike**: Low base load with sharp bursts (10 base, 100 peak)
- **step**: Sudden jumps between load levels (50/200/100/300/50)

### Experiment Configuration
- **Total runs**: 36 (18 per condition)
- **Patterns**: constant×3, step×5, spike×5, ramp×5 per condition
- **Run duration**: 10 minutes load + 2 minutes settle = 12 minutes
- **Total time**: ~7.2 hours

### Conditions
- **Condition A (Proactive)**: ML-driven autoscaling active
- **Condition B (Reactive)**: Standard HPA (CPU threshold 70%)

## Data Collection

### GKE Dataset
- **Total rows**: 3,115
- **Violations**: 377 (12.1%)
- **Threshold**: 35.68ms
- **Runs**: 25 experiments across 4 patterns + 1 mixed 4-hour run

### Local Dataset
- **Total rows**: 3,500
- **Violations**: 592 (16.9%)
- **Threshold**: 9.86ms

## Services

| Service | Port | Description |
|---------|------|-------------|
| Sock Shop | 80 | Microservices demo application |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboards (admin/foobar) |
| Kafka | 9092 | Message broker |
| Zookeeper | 2181 | Kafka coordination |

## Configuration

### Environment Variables
```yaml
metrics-aggregator:
  MODE: production              # or development
  POLL_INTERVAL_SEC: 30
  PROMETHEUS_URL: http://prometheus:9090

authoritative-scaler:
  VOTING_STRATEGY: majority     # majority, unanimous, weighted
  DECISION_WINDOW_SEC: 5

scaling-controller:
  SLO_THRESHOLD_MS: 35.68
  COOLDOWN_MINUTES: 5
  MIN_REPLICAS: 1
  MAX_REPLICAS: 10
```

## Monitoring

### View Logs
```bash
# All services
docker-compose -f docker-compose.ml.yml logs -f

# Specific service
docker-compose -f docker-compose.ml.yml logs -f authoritative-scaler
```

### Kafka Topics
```bash
# View metrics
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic metrics

# View votes
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic model-votes
```

## Academic Integrity

This implementation is designed for educational and research purposes. All components are original work based on:
- Weaveworks Sock Shop demo (open source)
- Scikit-learn ML models (trained on collected data)
- Apache Kafka (open source message broker)
- Custom-built services (metrics aggregator, inference, scaler)

## References

- Sock Shop: https://github.com/microservices-demo/microservices-demo
- Kafka: https://kafka.apache.org/
- Scikit-learn: https://scikit-learn.org/
- XGBoost: https://xgboost.readthedocs.io/
