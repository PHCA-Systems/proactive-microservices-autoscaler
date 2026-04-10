# Requirements: GKE Data Collection Pipeline

## Introduction

This document defines the requirements for deploying the Sock Shop data collection pipeline to GCP/GKE and collecting a new metrics dataset for ML model retraining.

## Requirements

### 1. GKE Cluster Provisioning

**User Story**: As a researcher, I need a stable GKE cluster so that Sock Shop runs in a real cloud environment without interruption during experiments.

#### Acceptance Criteria

1.1 A GKE cluster named `sock-shop-cluster` SHALL be created in region `us-central1` with 3 nodes of type `e2-standard-4`.

1.2 The cluster SHALL have autoupgrade disabled (`--no-enable-autoupgrade`) to prevent node restarts during experiments.

1.3 After provisioning, `kubectl get nodes` SHALL show 3 nodes in `Ready` state.

1.4 Local `kubectl` SHALL be configured with cluster credentials via `gcloud container clusters get-credentials`.

---

### 2. Sock Shop Deployment

**User Story**: As a researcher, I need Sock Shop running on GKE with a public IP so that Locust can generate load against it.

#### Acceptance Criteria

2.1 A `sock-shop` namespace SHALL be created and the upstream Sock Shop manifest SHALL be applied from `https://raw.githubusercontent.com/microservices-demo/microservices-demo/master/deploy/kubernetes/complete-demo.yaml`.

2.2 All pods in the `sock-shop` namespace SHALL reach `Running` status before proceeding.

2.3 The `front-end` service SHALL be patched to type `LoadBalancer` and SHALL receive an external IP.

2.4 The external IP SHALL be reachable via HTTP (port 80) from the Locust VM.

---

### 3. Prometheus Deployment

**User Story**: As a researcher, I need Prometheus scraping Sock Shop metrics at 10-second intervals so that the metrics aggregator has sufficient resolution.

#### Acceptance Criteria

3.1 The `prometheus-community` Helm chart SHALL be installed into a `monitoring` namespace.

3.2 `scrape_interval` and `evaluation_interval` SHALL both be set to `5s` to match the local Prometheus configuration.

3.3 `alertmanager` and `pushgateway` SHALL be disabled.

3.4 Prometheus SHALL be accessible locally via `kubectl port-forward` on port 9090.

3.5 Sock Shop service metrics (e.g., `request_duration_seconds_count`) SHALL be visible in the Prometheus UI at `http://localhost:9090`.

---

### 4. Locust VM Setup

**User Story**: As a researcher, I need a dedicated GCE VM running Locust so that load generation is isolated from the GKE cluster and does not consume cluster resources.

#### Acceptance Criteria

4.1 A GCE instance named `locust-runner` SHALL be created with machine type `e2-small`, zone `us-central1-a`, image `ubuntu-2204-lts`.

4.2 Python 3 and Locust SHALL be installed on the VM.

4.3 The load testing scripts (`locustfile.py`, `load_shapes.py`, and per-pattern locustfiles) SHALL be copied from `kafka-structured/load-testing/src/` to the VM.

4.4 Locust SHALL be runnable in headless mode targeting the Sock Shop external IP.

---

### 5. Metrics Collection (Development Mode)

**User Story**: As a researcher, I need the metrics aggregator running locally in development mode so that it writes feature vectors to CSV without requiring Kafka.

#### Acceptance Criteria

5.1 A `kubectl port-forward` to `svc/prometheus-server` on port 9090 SHALL be active before starting the aggregator.

5.2 The metrics aggregator SHALL be started with `MODE=development`, `PROMETHEUS_URL=http://localhost:9090`, `POLL_INTERVAL_SEC=30`, and `OUTPUT_DIR=./output`.

5.3 The aggregator SHALL write rows to `kafka-structured/services/metrics-aggregator/output/sockshop_metrics.csv` (or the configured `OUTPUT_DIR`).

5.4 Each poll cycle SHALL produce one CSV row per Sock Shop service (up to 8 services: `carts`, `catalogue`, `front-end`, `orders`, `payment`, `queue-master`, `shipping`, `user`).

5.5 The CSV schema SHALL match the existing dataset: `timestamp`, `service`, `request_rate_rps`, `error_rate_pct`, `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms`, `cpu_usage_pct`, `memory_usage_mb`, `delta_rps`, `delta_p95_latency_ms`, `delta_cpu_usage_pct`, `sla_violated`.

---

### 6. Load Experiment Execution

**User Story**: As a researcher, I need to run four distinct load patterns so that the collected dataset covers diverse traffic conditions for robust ML training.

#### Acceptance Criteria

6.1 Four load patterns SHALL be executed: Constant (20 min, 50 users), Ramp (10 min, 10→150→10 users), Spike (10 min, base 10 + spikes to 100), Step (10 min, 50→200→100→300→50 users).

6.2 Each experiment run SHALL have the metrics aggregator and port-forward active for the full duration.

6.3 The resulting CSV SHALL contain data rows spanning the experiment duration at 30-second intervals.

6.4 After all experiments, the collected CSV SHALL be copied to `kafka-structured/output/csv/` alongside existing datasets.

---

### 7. Cost Management and Teardown

**User Story**: As a researcher, I need to pause and resume the cluster between sessions so that GCP compute costs are minimized.

#### Acceptance Criteria

7.1 After each session, the GKE cluster SHALL be resized to 0 nodes to stop compute billing while preserving deployments.

7.2 The Locust VM SHALL be stopped between sessions.

7.3 The cluster SHALL be resumable by resizing back to 3 nodes and starting the VM, with all deployments intact.

7.4 Full teardown (cluster deletion) SHALL be documented for when data collection is complete.
