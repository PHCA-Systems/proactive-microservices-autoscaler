# System Architecture Guide

## Overview

This document describes the complete architecture for the ML-driven proactive autoscaling system, including both the application architecture and the GKE infrastructure setup.

## Table of Contents

1. [System Components](#system-components)
2. [Data Flow](#data-flow)
3. [Message Formats](#message-formats)
4. [GKE Infrastructure](#gke-infrastructure)
5. [Network Configuration](#network-configuration)
6. [Operating Modes](#operating-modes)

---

## System Components

### 1. Metrics Aggregator Service
**Purpose**: Poll Prometheus metrics and publish to Kafka

**Responsibilities**:
- Poll Prometheus every 30 seconds for per-service metrics
- Build feature vectors from raw metrics (RPS, latency, CPU, memory, deltas)
- Publish metrics to Kafka topic `metrics`
- **Production Mode**: Publish feature vectors for ML inference
- **Development Mode**: Write raw metrics to CSV for model retraining

### 2. ML Inference Services (3 instances)
**Models**: XGBoost, Random Forest, Logistic Regression

**Responsibilities**:
- Subscribe to Kafka topic `metrics`
- Receive feature vectors for each service
- Run inference to predict SLA violations
- Publish predictions (votes) to Kafka topic `model-votes`
- **Production Mode**: Save predictions to CSV for model retraining
- **Development Mode**: Inactive (no inference)

### 3. Authoritative Scaling Service
**Purpose**: Aggregate model votes and make scaling decisions

**Responsibilities**:
- Subscribe to Kafka topic `model-votes`
- Collect votes from all 3 ML models for each service
- Apply voting strategy (majority vote)
- Publish decisions to Kafka topic `scaling-decisions`
- Log which models voted for what action per service

### 4. Scaling Controller
**Purpose**: Execute scaling decisions via Kubernetes API

**Responsibilities**:
- Subscribe to Kafka topic `scaling-decisions`
- On SCALE_UP: Identify bottleneck service, call K8s API
- Bottleneck selection: Service with highest (p95_latency / SLO_threshold) ratio
- Scale quantity: +1 replica
- Cooldown: 5 minutes per service after any scale event
- RBAC: Dedicated ServiceAccount with scoped permissions

**Scale-Down Policy** (separate loop, NOT ML-driven):
- Runs every 30 seconds independently
- Conditions (ALL must hold for 10 consecutive intervals = 5 minutes):
  1. CPU utilization < 30%
  2. p95 latency < 0.7 × SLO threshold (25.2 ms)
  3. Current replicas > 1
  4. Service not in 5-minute cooldown
- Scale quantity: −1 replica

### 5. Kafka Message Broker
**Topics**:
- `metrics`: Raw feature vectors from metrics aggregator
- `model-votes`: Prediction votes from ML inference services
- `scaling-decisions`: Final decisions from authoritative scaler

**Purpose**: Decouple services and enable real-time streaming

---

## Data Flow

```
┌─────────────┐
│ Prometheus  │
└──────┬──────┘
       │ Poll every 30s
       ▼
┌──────────────────────┐
│ Metrics Aggregator   │
└──────┬───────────────┘
       │ Publish feature vectors
       ▼
┌──────────────────────┐
│ Kafka: "metrics"     │
└──┬────┬────┬─────────┘
   │    │    │
   ▼    ▼    ▼
┌─────┐ ┌─────┐ ┌─────┐
│ XGB │ │ RF  │ │ LR  │
└──┬──┘ └──┬──┘ └──┬──┘
   │       │       │
   └───────┼───────┘
           ▼
┌──────────────────────┐
│ Kafka: "model-votes" │
└──────────┬───────────┘
           ▼
┌──────────────────────────┐
│ Authoritative Scaler     │
└──────────┬───────────────┘
           ▼
┌──────────────────────────────┐
│ Kafka: "scaling-decisions"   │
└──────────┬───────────────────┘
           ▼
┌──────────────────────┐
│ Scaling Controller   │
└──────────┬───────────┘
           ▼
    K8s API → Scale Deployments
```

---

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

### Scaling Decision Message
```json
{
  "timestamp": "2026-04-04T12:30:02Z",
  "service": "orders",
  "decision": "SCALE_UP",
  "votes": {
    "xgboost": {"prediction": 1, "confidence": 0.87},
    "random_forest": {"prediction": 1, "confidence": 0.82},
    "logistic_regression": {"prediction": 0, "confidence": 0.55}
  },
  "vote_count": {"SCALE_UP": 2, "NO_OP": 1}
}
```

---

## GKE Infrastructure

### Cluster Configuration
- **Name**: sock-shop-cluster
- **Location**: us-central1-a
- **Nodes**: 3× e2-standard-4 (4 vCPU, 16 GB RAM each)
- **Total Resources**: 12 vCPUs, 48 GB RAM
- **Master IP**: 34.66.13.244

### Namespaces

#### sock-shop Namespace
**Contains**:
- 7 monitored microservices: front-end, carts, orders, catalogue, user, payment, shipping
- 4 infrastructure services: catalogue-db, carts-db, orders-db, user-db, session-db, rabbitmq, queue-master
- Prometheus server (exposed via LoadBalancer)
- HPA (conditionally enabled for reactive baseline)

#### pipeline Namespace
**Contains**:
- Kafka + Zookeeper
- Metrics Aggregator
- ML Inference Services (3 pods)
- Authoritative Scaler
- Scaling Controller
- Event Store (InfluxDB)

---

## Network Configuration

### Prometheus Exposure
Prometheus in sock-shop namespace is accessible from pipeline namespace:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: prometheus-server-external
  namespace: sock-shop
spec:
  type: LoadBalancer
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
```

### Scaling Controller RBAC

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: scaling-controller-sa
  namespace: sock-shop
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: scaling-controller-role
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "deployments/scale"]
  verbs: ["get", "list", "patch", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scaling-controller-binding
subjects:
- kind: ServiceAccount
  name: scaling-controller-sa
  namespace: sock-shop
roleRef:
  kind: ClusterRole
  name: scaling-controller-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Operating Modes

### Production Mode
```bash
docker-compose --profile production up
```
- Metrics aggregator publishes feature vectors to Kafka
- All 3 ML inference services are active
- Models publish votes to `model-votes` topic
- Authoritative scaling service outputs decisions
- Scaling controller executes decisions
- Predictions saved to CSV for future retraining

### Development Mode
```bash
docker-compose --profile development up
```
- Metrics aggregator writes raw metrics to CSV
- ML inference services are inactive
- Focus on data collection for model retraining
- No Kafka message flow

### Switching Between Experimental Conditions

**Enable Proactive (Condition A)**:
```bash
kubectl delete -f k8s/hpa-baseline.yaml --ignore-not-found
kubectl scale deployment scaling-controller -n sock-shop --replicas=1
```

**Enable Reactive (Condition B)**:
```bash
kubectl scale deployment scaling-controller -n sock-shop --replicas=0
kubectl apply -f k8s/hpa-baseline.yaml
```

---

## Configuration

### Environment Variables

**Metrics Aggregator**:
```yaml
MODE: production              # or development
POLL_INTERVAL_SEC: 30
PROMETHEUS_URL: http://prometheus:9090
```

**Authoritative Scaler**:
```yaml
VOTING_STRATEGY: majority     # majority, unanimous, weighted
DECISION_WINDOW_SEC: 5
```

**Scaling Controller**:
```yaml
NAMESPACE: sock-shop
SLO_THRESHOLD_MS: 35.68
COOLDOWN_MINUTES: 5
MIN_REPLICAS: 1
MAX_REPLICAS: 10
SCALEDOWN_CPU_PCT: 30.0
SCALEDOWN_LAT_RATIO: 0.7
SCALEDOWN_WINDOW: 10
```

---

## Methodological Benefits

### No Resource Contention
- Sock Shop runs in isolation
- Pipeline overhead doesn't affect Sock Shop metrics
- Both conditions see identical Sock Shop environment

### Preserves Calibration
- SLO threshold (35.68ms) remains valid
- Training data remains valid
- ML models don't need retraining

### Fair Comparison
- **Proactive condition**: Pipeline active
- **Reactive condition**: Only HPA active
- **Both see same Sock Shop baseline performance**

---

## Cost Summary

**GKE Cluster**:
- 3 nodes × e2-standard-4
- Cost: ~$0.40/hour
- Total resources: 12 vCPUs, 48 GB RAM

**Total experiment cost**:
- Hourly: $0.40/hour
- 7.2-hour experiment: ~$2.88

---

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

# View decisions
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scaling-decisions
```

### Access Dashboards
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / foobar)
- Sock Shop: http://localhost:80
