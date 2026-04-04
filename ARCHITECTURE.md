# ML-Driven Proactive Autoscaling Architecture

## Overview

This document describes the enhanced architecture for integrating machine learning-based SLA violation prediction into the Sock Shop microservices demo using Kafka as a message broker for real-time metrics streaming and model inference.

## System Components

### 1. Metrics Aggregator Service
- **Purpose**: Poll Prometheus metrics and publish to Kafka
- **Responsibilities**:
  - Poll Prometheus every 30 seconds for per-service metrics
  - Build feature vectors from raw metrics (RPS, latency, CPU, memory, deltas)
  - Publish metrics to Kafka topic `metrics`
  - **Production Mode**: Publish feature vectors for ML inference
  - **Development Mode**: Write raw metrics to CSV for model retraining

### 2. ML Inference Services (3 instances)
- **Models**: XGBoost, Random Forest, Logistic Regression
- **Responsibilities**:
  - Subscribe to Kafka topic `metrics`
  - Receive feature vectors for each service
  - Run inference to predict SLA violations
  - Publish predictions (votes) to Kafka topic `model-votes`
  - **Production Mode**: Save predictions to CSV for model retraining
  - **Development Mode**: Inactive (no inference)

### 3. Authoritative Scaling Service
- **Purpose**: Aggregate model votes and make scaling decisions
- **Responsibilities**:
  - Subscribe to Kafka topic `model-votes`
  - Collect votes from all 3 ML models for each service
  - Apply voting strategy (majority vote, weighted average, etc.)
  - Output scaling decisions in human-readable format
  - Log which models voted for what action per service

### 4. Kafka Message Broker
- **Topics**:
  - `metrics`: Raw feature vectors from metrics aggregator
  - `model-votes`: Prediction votes from ML inference services
- **Purpose**: Decouple services and enable real-time streaming

## Data Flow

```
┌─────────────┐
│ Prometheus  │
└──────┬──────┘
       │ Poll every 30s
       ▼
┌──────────────────────┐
│ Metrics Aggregator   │
│ Service              │
└──────┬───────────────┘
       │ Publish feature vectors
       ▼
┌──────────────────────┐
│ Kafka Topic:         │
│ "metrics"            │
└──┬────┬────┬─────────┘
   │    │    │
   │    │    └─────────────┐
   │    │                  │
   │    └──────────┐       │
   │               │       │
   ▼               ▼       ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ XGBoost │  │ Random  │  │Logistic │
│ Service │  │ Forest  │  │Regress. │
│         │  │ Service │  │ Service │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     │ Vote       │ Vote       │ Vote
     │            │            │
     └────────┬───┴────────────┘
              ▼
┌──────────────────────────┐
│ Kafka Topic:             │
│ "model-votes"            │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Authoritative Scaling    │
│ Service                  │
└──────────────────────────┘
           │
           ▼
    Scaling Decisions
    (Console Output)
```

## Message Formats

### Metrics Topic Message
```json
{
  "timestamp": "2026-04-04T12:30:00Z",
  "service": "orders",
  "features": {
    "request_rate_rps": 150.5,
    "error_rate_pct": 2.3,
    "p50_latency_ms": 45.2,
    "p95_latency_ms": 120.5,
    "p99_latency_ms": 180.3,
    "cpu_usage_pct": 75.2,
    "memory_usage_mb": 512.8,
    "delta_rps": 25.3,
    "delta_p95_latency_ms": 15.2,
    "delta_cpu_usage_pct": 10.5
  }
}
```

### Model Votes Topic Message
```json
{
  "timestamp": "2026-04-04T12:30:01Z",
  "service": "orders",
  "model": "xgboost",
  "prediction": 1,
  "probability": 0.87,
  "confidence": 0.87
}
```

### Scaling Decision Output
```
=== SCALING DECISIONS @ 2026-04-04 12:30:02 ===

Service: orders
  XGBoost:           SCALE UP   (87% confidence)
  Random Forest:     SCALE UP   (82% confidence)
  Logistic Regress:  NO ACTION  (45% confidence)
  
  DECISION: SCALE UP (2/3 models agree)

Service: payment
  XGBoost:           NO ACTION  (92% confidence)
  Random Forest:     NO ACTION  (88% confidence)
  Logistic Regress:  NO ACTION  (91% confidence)
  
  DECISION: NO ACTION (3/3 models agree)
```

## Operating Modes

### Production Mode
```bash
docker-compose --profile production up
```
- Metrics aggregator publishes feature vectors to Kafka
- All 3 ML inference services are active
- Models publish votes to `model-votes` topic
- Authoritative scaling service outputs decisions
- Predictions saved to CSV for future retraining

### Development Mode
```bash
docker-compose --profile development up
```
- Metrics aggregator writes raw metrics to CSV
- ML inference services are inactive
- Focus on data collection for model retraining
- No Kafka message flow

## Docker Compose Services

### New Services to Add
1. `kafka` - Kafka broker
2. `zookeeper` - Kafka dependency
3. `metrics-aggregator` - Python service
4. `ml-xgboost` - XGBoost inference service
5. `ml-random-forest` - Random Forest inference service
6. `ml-logistic-regression` - Logistic Regression inference service
7. `authoritative-scaler` - Voting aggregator service

### Service Dependencies
```yaml
metrics-aggregator:
  depends_on:
    - kafka
    - prometheus

ml-xgboost:
  depends_on:
    - kafka
    - metrics-aggregator

authoritative-scaler:
  depends_on:
    - kafka
    - ml-xgboost
    - ml-random-forest
    - ml-logistic-regression
```

## Configuration

### Environment Variables
- `MODE`: `production` or `development`
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address
- `PROMETHEUS_URL`: Prometheus endpoint
- `POLL_INTERVAL_SEC`: Metrics polling interval (default: 30)
- `MODEL_PATH`: Path to trained model file

## Implementation Phases

### Phase 1: Kafka Infrastructure
- Add Kafka and Zookeeper to docker-compose
- Create topics: `metrics`, `model-votes`
- Test basic pub/sub

### Phase 2: Metrics Aggregator Service
- Refactor `collect_metrics.py` into a service
- Add Kafka producer functionality
- Implement mode switching (production/development)
- Add feature vector building logic

### Phase 3: ML Inference Services
- Create Dockerfiles for each model
- Implement Kafka consumer for `metrics` topic
- Implement Kafka producer for `model-votes` topic
- Load pre-trained models from ML-Models directory
- Add inference logic with error handling

### Phase 4: Authoritative Scaling Service
- Implement Kafka consumer for `model-votes` topic
- Build vote aggregation logic
- Implement voting strategies (majority, weighted, etc.)
- Create human-readable output formatter
- Add logging and monitoring

### Phase 5: Integration & Testing
- Test end-to-end flow with Locust load generator
- Validate message formats and timing
- Performance testing and optimization
- Documentation and deployment guides

## Model Organization

The ML models are located in `ML-Models/` directory:
```
ML-Models/
├── models/
│   ├── xgboost/
│   │   ├── model.joblib
│   │   ├── parameters.json
│   │   └── metrics.json
│   ├── random_forest/
│   │   ├── model.joblib
│   │   ├── parameters.json
│   │   └── metrics.json
│   └── logistic_regression/
│       ├── model.joblib
│       ├── parameters.json
│       └── metrics.json
├── config.py
├── preprocessing.py
└── inference_example.py
```

Each model directory contains:
- `model.joblib`: Trained scikit-learn model
- `parameters.json`: Service mapping and hyperparameters
- `metrics.json`: Model performance metrics

## Next Steps

1. Review and approve architecture
2. Organize ML models into proper structure
3. Implement Kafka infrastructure
4. Build metrics aggregator service
5. Create ML inference services
6. Implement authoritative scaling service
7. Test and validate end-to-end
