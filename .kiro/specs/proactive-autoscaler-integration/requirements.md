# Requirements Document: Proactive Autoscaler Integration

## Introduction

This requirements document specifies the functional and non-functional requirements for a proactive, context-aware microservice autoscaling system. The system integrates machine learning classifiers with Kubernetes autoscaling through a Kafka-based event-driven architecture. The system is designed for a graduation research project evaluating proactive autoscaling against reactive HPA baselines using the Sock Shop microservices benchmark on Google Kubernetes Engine.

The system completes an existing Kafka pipeline by adding: (1) decision publishing from the authoritative scaler, (2) a scaling controller that executes Kubernetes API calls, (3) experiment orchestration tooling for 34 automated runs, and (4) results analysis with statistical comparison.

## Glossary

- **Authoritative_Scaler**: Service that aggregates ML model votes and makes consensus scaling decisions
- **Bottleneck_Service**: The microservice with the highest ratio of p95 latency to SLO threshold
- **Cooldown_Period**: 5-minute window after a scaling event during which no further scaling is allowed for that service
- **Decision_Message**: Kafka message containing consensus scaling decision (SCALE_UP or NO_OP)
- **Experiment_Runner**: Service that orchestrates automated experimental runs with condition switching
- **HPA**: Horizontal Pod Autoscaler (Kubernetes reactive autoscaling baseline)
- **Metrics_Aggregator**: Service that polls Prometheus and publishes feature vectors to Kafka
- **Metrics_Message**: Kafka message containing service metrics (latency, CPU, memory, request rate)
- **ML_Inference_Service**: Service that consumes metrics and publishes model predictions
- **Proactive_Condition**: Experimental condition using ML-based scaling controller
- **Reactive_Condition**: Experimental condition using CPU-based HPA
- **Results_Analyzer**: Service that computes statistical comparisons from experiment data
- **Scaling_Controller**: Service that executes scaling decisions via Kubernetes API
- **Scaling_Event**: Record of a scaling action with timestamp, service, direction, and replica counts
- **SLO_Threshold**: Service Level Objective for p95 latency (36ms for front-end service)
- **Vote_Message**: Kafka message containing a single ML model's scaling prediction

## Requirements

### Requirement 1: Authoritative Scaler Decision Publishing

**User Story:** As a system integrator, I want the authoritative scaler to publish consensus decisions to Kafka, so that the scaling controller can consume and execute them.

#### Acceptance Criteria

1. WHEN the Authoritative_Scaler receives votes from all 3 ML models, THE Authoritative_Scaler SHALL compute a majority consensus decision
2. WHEN the consensus decision is computed, THE Authoritative_Scaler SHALL publish a Decision_Message to the scaling-decisions Kafka topic
3. THE Decision_Message SHALL include timestamp, service name, decision (SCALE_UP or NO_OP), original votes, consensus type, and vote counts
4. WHEN fewer than 3 votes are received within 5 seconds, THE Authoritative_Scaler SHALL make a decision based on available votes
5. WHEN 2 or more models vote SCALE_UP, THE Authoritative_Scaler SHALL set the decision to SCALE_UP
6. WHEN fewer than 2 models vote SCALE_UP, THE Authoritative_Scaler SHALL set the decision to NO_OP

### Requirement 2: Scaling Controller Scale-Up Execution

**User Story:** As a system operator, I want the scaling controller to execute scale-up decisions, so that services can respond to predicted load increases.

#### Acceptance Criteria

1. WHEN a Decision_Message with decision SCALE_UP is consumed, THE Scaling_Controller SHALL identify the Bottleneck_Service
2. THE Bottleneck_Service SHALL be selected as the service with the highest ratio of p95_latency_ms to SLO_Threshold
3. WHEN the Bottleneck_Service is in the Cooldown_Period, THE Scaling_Controller SHALL skip the scaling action
4. WHEN the Bottleneck_Service is not in the Cooldown_Period, THE Scaling_Controller SHALL query the current replica count from Kubernetes API
5. WHEN the current replica count is less than MAX_REPLICAS (10), THE Scaling_Controller SHALL increment the replica count by 1
6. WHEN the replica count is updated, THE Scaling_Controller SHALL record a Scaling_Event with direction SCALE_UP
7. WHEN a Scaling_Event is recorded, THE Scaling_Controller SHALL start a Cooldown_Period for that service

### Requirement 3: Scaling Controller Scale-Down Policy

**User Story:** As a system operator, I want the scaling controller to scale down over-provisioned services, so that resource utilization is optimized.

#### Acceptance Criteria

1. THE Scaling_Controller SHALL evaluate scale-down conditions every 30 seconds for all monitored services
2. WHEN a service has CPU utilization below 30% for 10 consecutive intervals, AND p95 latency below 0.7 × SLO_Threshold for 10 consecutive intervals, AND current replicas greater than MIN_REPLICAS (1), AND not in Cooldown_Period, THE Scaling_Controller SHALL decrement the replica count by 1
3. WHEN the replica count is decremented, THE Scaling_Controller SHALL record a Scaling_Event with direction SCALE_DOWN
4. THE Scaling_Controller SHALL maintain a rolling window of the last 10 metric snapshots per service

### Requirement 4: Scaling Controller Kubernetes Integration

**User Story:** As a system operator, I want the scaling controller to interact with Kubernetes API securely, so that scaling actions are executed with proper authorization.

#### Acceptance Criteria

1. THE Scaling_Controller SHALL use a dedicated ServiceAccount with RBAC permissions limited to get, list, patch, and update on deployments and deployments/scale
2. WHEN querying current replicas, THE Scaling_Controller SHALL call GET /apis/apps/v1/namespaces/sock-shop/deployments/{service}
3. WHEN updating replicas, THE Scaling_Controller SHALL call PATCH /apis/apps/v1/namespaces/sock-shop/deployments/{service}/scale
4. WHEN a Kubernetes API call fails, THE Scaling_Controller SHALL log the error and continue operation for other services
5. THE Scaling_Controller SHALL enforce MIN_REPLICAS (1) and MAX_REPLICAS (10) bounds on all scaling actions

### Requirement 5: Scaling Event Logging

**User Story:** As a researcher, I want all scaling events logged with detailed metadata, so that I can analyze system behavior during experiments.

#### Acceptance Criteria

1. WHEN a scaling action is executed, THE Scaling_Controller SHALL write a Scaling_Event to a JSONL log file
2. THE Scaling_Event SHALL include timestamp (ISO 8601), service name, direction (SCALE_UP or SCALE_DOWN), old replica count, new replica count, and reason
3. THE Scaling_Controller SHALL append to the log file without overwriting previous entries
4. THE Scaling_Controller SHALL log to the path specified by environment variable SCALE_EVENT_LOG

### Requirement 6: Experiment Runner Orchestration

**User Story:** As a researcher, I want automated orchestration of 34 experimental runs, so that I can collect consistent data across conditions and patterns.

#### Acceptance Criteria

1. THE Experiment_Runner SHALL generate a run schedule with 34 runs: 2 conditions × (2 constant + 5 step + 5 spike + 5 ramp repetitions)
2. WHEN executing a run, THE Experiment_Runner SHALL reset all monitored service deployments to 1 replica
3. WHEN the Proactive_Condition is selected, THE Experiment_Runner SHALL delete HPA resources and scale the Scaling_Controller deployment to 1 replica
4. WHEN the Reactive_Condition is selected, THE Experiment_Runner SHALL apply HPA manifests and scale the Scaling_Controller deployment to 0 replicas
5. WHEN a run starts, THE Experiment_Runner SHALL start the load generator with the specified pattern (constant, step, spike, or ramp)
6. THE Experiment_Runner SHALL collect metric snapshots every 30 seconds for 12 minutes (24 intervals)
7. WHEN the load duration completes, THE Experiment_Runner SHALL stop the load generator and wait 3 minutes for settling
8. WHEN a run completes, THE Experiment_Runner SHALL write snapshots to a JSONL file named {condition}_{pattern}_run{id:02d}.jsonl

### Requirement 7: Experiment Metrics Collection

**User Story:** As a researcher, I want comprehensive metrics collected during experiments, so that I can evaluate system performance.

#### Acceptance Criteria

1. WHEN collecting a snapshot, THE Experiment_Runner SHALL query replica counts for all 7 monitored services from Kubernetes API
2. WHEN collecting a snapshot, THE Experiment_Runner SHALL query p95 latency and CPU utilization for all 7 monitored services
3. THE snapshot SHALL include timestamp, run_id, condition, pattern, interval_idx, and per-service metrics (replicas, p95_ms, cpu_pct, slo_violated)
4. WHEN p95 latency exceeds SLO_Threshold (36ms), THE Experiment_Runner SHALL set slo_violated to true for that service

### Requirement 8: Results Analysis Statistical Comparison

**User Story:** As a researcher, I want statistical comparison of proactive vs reactive conditions, so that I can validate the research hypothesis.

#### Acceptance Criteria

1. THE Results_Analyzer SHALL read all JSONL snapshot files from the experiments/results directory
2. WHEN computing per-run metrics, THE Results_Analyzer SHALL calculate SLO violation rate as the fraction of intervals where front-end p95 exceeds SLO_Threshold
3. WHEN computing per-run metrics, THE Results_Analyzer SHALL calculate total replica-seconds as the sum of (replicas × 30 seconds) across all services and intervals
4. THE Results_Analyzer SHALL aggregate runs by condition (proactive vs reactive) and pattern (constant, step, spike, ramp)
5. WHEN comparing conditions, THE Results_Analyzer SHALL apply Mann-Whitney U test for each metric × pattern combination
6. THE Results_Analyzer SHALL write per-run summary to experiments/results/summary.csv
7. THE Results_Analyzer SHALL write statistical test results to experiments/results/statistics.csv

### Requirement 9: ML Model Integration

**User Story:** As a system integrator, I want the correct trained models loaded into inference services, so that predictions are based on validated models.

#### Acceptance Criteria

1. THE ML_Inference_Service for Logistic Regression SHALL load the model from ML-Models/gke/models_mixed_standard/model_lr.joblib
2. THE ML_Inference_Service for Random Forest SHALL load the model from ML-Models/gke/models_mixed_standard/model_rf.joblib
3. THE ML_Inference_Service for XGBoost SHALL load the model from ML-Models/gke/models_mixed_standard/model_xgb.joblib
4. WHEN a model file is not found, THE ML_Inference_Service SHALL log an error and exit with non-zero status code
5. WHEN a model is loaded, THE ML_Inference_Service SHALL log the model type and file path

### Requirement 10: Reactive HPA Baseline Configuration

**User Story:** As a researcher, I want a standard CPU-based HPA baseline, so that I can compare proactive autoscaling against industry-standard reactive autoscaling.

#### Acceptance Criteria

1. THE HPA baseline SHALL target 70% average CPU utilization for all 7 monitored services
2. THE HPA baseline SHALL set minReplicas to 1 and maxReplicas to 10 for all services
3. THE HPA baseline SHALL configure a scale-down stabilization window of 300 seconds (5 minutes)
4. WHEN the Reactive_Condition is enabled, THE HPA resources SHALL be applied to the sock-shop namespace
5. WHEN the Proactive_Condition is enabled, THE HPA resources SHALL be deleted from the sock-shop namespace

### Requirement 11: System Performance

**User Story:** As a system operator, I want low-latency scaling decisions, so that the system responds quickly to load changes.

#### Acceptance Criteria

1. WHEN metrics are published to Kafka, THE ML_Inference_Service SHALL produce a prediction within 1 second
2. WHEN votes are published to Kafka, THE Authoritative_Scaler SHALL produce a consensus decision within 5 seconds
3. WHEN a Decision_Message is consumed, THE Scaling_Controller SHALL execute the Kubernetes API call within 2 seconds
4. THE end-to-end latency from metric collection to scaling execution SHALL be less than 40 seconds on average

### Requirement 12: System Reliability

**User Story:** As a system operator, I want the system to handle failures gracefully, so that transient errors do not disrupt autoscaling.

#### Acceptance Criteria

1. WHEN a Kafka broker is unreachable, THE service SHALL retry connection with exponential backoff up to 60 seconds
2. WHEN a Kubernetes API call returns an error, THE Scaling_Controller SHALL log the error and continue processing other services
3. WHEN a deployment is not found, THE Scaling_Controller SHALL log a warning and skip that service
4. WHEN fewer than 3 model votes are received within 5 seconds, THE Authoritative_Scaler SHALL make a decision based on available votes

### Requirement 13: Experiment Validation

**User Story:** As a researcher, I want validation checks before running the full experiment, so that I can detect configuration errors early.

#### Acceptance Criteria

1. WHEN the Experiment_Runner starts, THE Experiment_Runner SHALL verify that all 7 monitored service deployments exist in the sock-shop namespace
2. WHEN the Experiment_Runner starts, THE Experiment_Runner SHALL verify that the Scaling_Controller deployment exists
3. WHEN the Experiment_Runner starts, THE Experiment_Runner SHALL verify that the load generator script is executable
4. WHEN validation fails, THE Experiment_Runner SHALL log the error and exit with non-zero status code

### Requirement 14: Deployment Environment Constraints

**User Story:** As a system operator, I want the system deployed on GKE with specific configuration, so that experiments run in a controlled environment.

#### Acceptance Criteria

1. THE system SHALL be deployed on Google Kubernetes Engine in region us-central1
2. THE GKE cluster SHALL have a node pool with 3 nodes of type e2-standard-4 (4 vCPU, 16 GB RAM each)
3. THE Sock Shop benchmark SHALL be deployed in the sock-shop namespace
4. THE system SHALL monitor exactly 7 services: front-end, carts, orders, catalogue, user, payment, shipping

### Requirement 15: Configuration Management

**User Story:** As a system operator, I want system parameters configurable via environment variables, so that I can adjust behavior without code changes.

#### Acceptance Criteria

1. THE Scaling_Controller SHALL read NAMESPACE, KAFKA_BOOTSTRAP_SERVERS, SLO_THRESHOLD_MS, COOLDOWN_MINUTES, MIN_REPLICAS, MAX_REPLICAS, SCALEDOWN_CPU_PCT, SCALEDOWN_LAT_RATIO, and SCALEDOWN_WINDOW from environment variables
2. WHEN an environment variable is not set, THE Scaling_Controller SHALL use a documented default value
3. THE Experiment_Runner SHALL read configuration from run_config.py including SLO_THRESHOLD_MS, NAMESPACE, POLL_INTERVAL_S, and MONITORED_SERVICES
4. THE ML_Inference_Service SHALL read KAFKA_BOOTSTRAP_SERVERS and MODEL_PATH from environment variables

### Requirement 16: Security and Access Control

**User Story:** As a security engineer, I want minimal privilege access controls, so that services cannot perform unauthorized actions.

#### Acceptance Criteria

1. THE Scaling_Controller ServiceAccount SHALL have permissions limited to get, list, patch, and update on deployments and deployments/scale resources
2. THE Scaling_Controller ServiceAccount SHALL NOT have cluster-admin or namespace-admin privileges
3. THE Scaling_Controller ServiceAccount SHALL have permissions scoped to the sock-shop namespace only
4. WHEN RBAC permissions are insufficient, THE Kubernetes API SHALL return 403 Forbidden and the Scaling_Controller SHALL log the error

### Requirement 17: Data Validation

**User Story:** As a system integrator, I want Kafka messages validated against schemas, so that malformed data does not cause failures.

#### Acceptance Criteria

1. WHEN a Metrics_Message is consumed, THE ML_Inference_Service SHALL verify that the service field is one of the 7 monitored services
2. WHEN a Vote_Message is consumed, THE Authoritative_Scaler SHALL verify that the model field is one of ["lr", "rf", "xgb"]
3. WHEN a Vote_Message is consumed, THE Authoritative_Scaler SHALL verify that the prediction field is 0 or 1
4. WHEN a Decision_Message is consumed, THE Scaling_Controller SHALL verify that the decision field is "SCALE_UP" or "NO_OP"
5. WHEN message validation fails, THE service SHALL log a warning and skip processing that message

### Requirement 18: Experiment Pause and Review

**User Story:** As a researcher, I want the system to pause before starting overnight experiments, so that I can verify readiness.

#### Acceptance Criteria

1. WHEN the Experiment_Runner is invoked with the --pause-before-start flag, THE Experiment_Runner SHALL print the run schedule and wait for user confirmation
2. WHEN user confirmation is received, THE Experiment_Runner SHALL proceed with the experiment schedule
3. THE Experiment_Runner SHALL display estimated total experiment time before starting

### Requirement 19: Results Output Format

**User Story:** As a researcher, I want results in CSV format, so that I can import them into statistical analysis tools.

#### Acceptance Criteria

1. THE summary.csv file SHALL have columns: run_id, condition, pattern, slo_violation_rate, total_replica_seconds, mean_replicas, peak_replicas
2. THE statistics.csv file SHALL have columns: pattern, metric, proactive_mean, proactive_std, reactive_mean, reactive_std, u_statistic, p_value, significant
3. WHEN p_value is less than 0.05, THE Results_Analyzer SHALL set the significant column to true
4. THE Results_Analyzer SHALL output a console table with formatted results for inclusion in the research paper

### Requirement 20: Virtual Environment Usage

**User Story:** As a developer, I want to use the existing virtual environment, so that I do not waste time reinstalling dependencies.

#### Acceptance Criteria

1. THE system SHALL use the virtual environment located at kafka-structured/services/metrics-aggregator/venv/
2. THE system SHALL NOT use MSYS Python (which is incompatible with required libraries)
3. WHEN dependencies are missing, THE system SHALL log an error listing the missing packages
