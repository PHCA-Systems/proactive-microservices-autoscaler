# Implementation Plan: Proactive Autoscaler Integration

## Overview

This implementation plan completes the proactive autoscaling system by integrating ML models with Kubernetes autoscaling through a Kafka-based pipeline. The system will be evaluated against reactive HPA baselines using 34 automated experimental runs on GKE with the Sock Shop benchmark.

The plan follows 8 phases: verification of existing components, integration of ML models, completion of the scaling controller, experiment tooling, GKE deployment, validation, execution (with pause point), and results analysis.

## Tasks

### Phase 1: Verification and Testing

- [x] 1. Verify existing Kafka pipeline components
  - Test metrics aggregator publishes to `metrics` topic
  - Test ML inference services consume from `metrics` topic
  - Test authoritative scaler consumes from `model-votes` topic
  - Verify all services connect to Kafka successfully
  - _Requirements: 1.1, 9.5, 12.1_

- [ ] 1.1 Write integration test for Kafka pipeline
  - Test end-to-end message flow from metrics → votes → decisions
  - Mock Prometheus responses and verify feature vector construction
  - _Requirements: 1.1, 1.2, 1.3_

### Phase 2: ML Model Integration

- [ ] 2. Plug in trained ML models to inference services
  - [x] 2.1 Update ML inference deployment manifests to mount model files
    - Configure volume mounts for `ML-Models/gke/models_mixed_standard/model_lr.joblib`
    - Configure volume mounts for `ML-Models/gke/models_mixed_standard/model_rf.joblib`
    - Configure volume mounts for `ML-Models/gke/models_mixed_standard/model_xgb.joblib`
    - Set MODEL_PATH environment variable for each service
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [x] 2.2 Verify model loading in ML inference services
    - Check logs for successful model loading messages
    - Verify model type and file path are logged
    - Test inference with sample feature vectors
    - _Requirements: 9.4, 9.5_
  
  - [ ] 2.3 Write unit tests for ML inference service
    - Test model loading with valid and invalid paths
    - Test prediction output format
    - Test vote message construction
    - _Requirements: 9.1, 9.2, 9.3_

### Phase 3: Authoritative Scaler Enhancement

- [ ] 3. Add Kafka producer to authoritative scaler
  - [x] 3.1 Implement DecisionsKafkaProducer class
    - Create producer for `scaling-decisions` topic
    - Implement publish_decision method with error handling
    - Add connection retry logic with exponential backoff
    - _Requirements: 1.2, 1.3, 12.1_
  
  - [x] 3.2 Integrate producer into decision loop
    - Call publish_decision after consensus is computed
    - Log successful decision publications
    - Handle Kafka publish failures gracefully
    - _Requirements: 1.2, 1.3, 12.1_
  
  - [x] 3.3 Test decision publishing
    - Verify decisions appear in `scaling-decisions` topic
    - Verify decision message format matches schema
    - Test with incomplete votes (timeout scenario)
    - _Requirements: 1.2, 1.3, 1.4, 17.3, 17.4_
  
  - [ ] 3.4 Write unit tests for majority voting logic
    - Test unanimous consensus (3-0 votes)
    - Test majority consensus (2-1 votes)
    - Test split decision (1-1-1 or 1-1 votes)
    - Test incomplete votes (1 or 2 models)
    - _Requirements: 1.5, 1.6, 12.4_

### Phase 4: Scaling Controller Completion

- [ ] 4. Complete scaling controller implementation
  - [x] 4.1 Implement scale-up logic
    - Consume from `scaling-decisions` topic
    - Implement bottleneck service selection (highest p95/SLO ratio)
    - Check cooldown period before scaling
    - Query current replicas from Kubernetes API
    - Increment replicas by 1 (enforce MAX_REPLICAS bound)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.5_
  
  - [x] 4.2 Implement scale-down policy
    - Consume from `metrics` topic for scale-down evaluation
    - Maintain rolling window of last 10 metric snapshots per service
    - Check conditions: CPU < 30%, p95 < 0.7×SLO, replicas > MIN_REPLICAS, not in cooldown
    - Decrement replicas by 1 when conditions met for 10 consecutive intervals
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 4.3 Implement cooldown tracking
    - Record timestamp after each scaling event
    - Check cooldown period (5 minutes) before allowing next scale
    - Maintain per-service cooldown state
    - _Requirements: 2.3, 2.7_
  
  - [x] 4.4 Implement scaling event logging
    - Write JSONL log entries for each scaling action
    - Include timestamp, service, direction, old/new replicas, reason
    - Append to log file specified by SCALE_EVENT_LOG env var
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 4.5 Add Kubernetes API error handling
    - Handle 403 Forbidden (RBAC permission errors)
    - Handle 404 Not Found (deployment doesn't exist)
    - Handle API call timeouts and network errors
    - Log errors and continue processing other services
    - _Requirements: 4.4, 12.2, 12.3_
  
  - [ ] 4.6 Write unit tests for scaling controller
    - Test bottleneck selection with various p95/SLO ratios
    - Test cooldown enforcement
    - Test min/max replica bounds
    - Test scale-down condition evaluation
    - Mock Kubernetes API responses
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 3.2, 4.5_

- [x] 5. Checkpoint - Test scaling controller with manual triggers
  - Manually publish SCALE_UP decision to Kafka
  - Verify replica count increases for bottleneck service
  - Verify cooldown prevents immediate re-scaling
  - Inject low CPU/latency metrics and verify scale-down after 10 intervals
  - Check scaling event log file for correct entries
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: Kubernetes RBAC and Configuration

- [ ] 6. Verify and apply Kubernetes RBAC manifests
  - [x] 6.1 Review scaling-controller-rbac.yaml
    - Verify ServiceAccount exists
    - Verify ClusterRole has minimal permissions (get, list, patch, update on deployments)
    - Verify ClusterRoleBinding links ServiceAccount to ClusterRole
    - Verify permissions scoped to sock-shop namespace only
    - _Requirements: 4.1, 16.1, 16.2, 16.3_
  
  - [x] 6.2 Apply RBAC manifests to GKE cluster
    - Apply ServiceAccount, ClusterRole, ClusterRoleBinding
    - Verify resources created successfully
    - Test scaling controller can query deployments
    - _Requirements: 4.1, 16.1_
  
  - [ ] 6.3 Test RBAC permission boundaries
    - Verify scaling controller cannot access resources outside sock-shop namespace
    - Verify scaling controller cannot perform unauthorized operations
    - _Requirements: 16.2, 16.3, 16.4_

- [ ] 7. Configure reactive HPA baseline
  - [x] 7.1 Review hpa-baseline.yaml
    - Verify HPA targets all 7 monitored services
    - Verify CPU target is 70% average utilization
    - Verify minReplicas=1, maxReplicas=10
    - Verify scale-down stabilization window is 300 seconds
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 7.2 Test HPA baseline application
    - Apply HPA manifests to sock-shop namespace
    - Verify HPA resources created for all 7 services
    - Delete HPA resources to test cleanup
    - _Requirements: 10.4, 10.5_

### Phase 6: Experiment Tooling

- [ ] 8. Complete experiment runner implementation
  - [x] 8.1 Implement run schedule generation
    - Generate 34 runs: 2 conditions × (2 constant + 5 step + 5 spike + 5 ramp)
    - Assign unique run IDs
    - Shuffle run order to avoid bias
    - _Requirements: 6.1_
  
  - [x] 8.2 Implement condition switching
    - Implement enable_proactive: delete HPA, scale controller to 1 replica
    - Implement enable_reactive: apply HPA, scale controller to 0 replicas
    - Implement reset_cluster: set all services to 1 replica
    - _Requirements: 6.3, 6.4, 10.4, 10.5_
  
  - [x] 8.3 Implement metrics collection
    - Query replica counts from Kubernetes API for all 7 services
    - Query p95 latency and CPU utilization from Prometheus
    - Construct snapshot with timestamp, run_id, condition, pattern, interval_idx
    - Calculate slo_violated flag (p95 > 36ms)
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 8.4 Implement run execution loop
    - Reset cluster before each run
    - Enable appropriate condition (proactive or reactive)
    - Start load generator with specified pattern
    - Collect snapshots every 30 seconds for 12 minutes (24 intervals)
    - Stop load generator and wait 3 minutes for settling
    - Write snapshots to JSONL file: {condition}_{pattern}_run{id:02d}.jsonl
    - _Requirements: 6.2, 6.5, 6.6, 6.7, 6.8_
  
  - [x] 8.5 Add experiment validation checks
    - Verify all 7 service deployments exist in sock-shop namespace
    - Verify scaling controller deployment exists
    - Verify load generator script is executable
    - Exit with error if validation fails
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [x] 8.6 Add pause-before-start flag
    - Print run schedule when --pause-before-start is used
    - Display estimated total experiment time (~8.5 hours)
    - Wait for user confirmation before proceeding
    - _Requirements: 18.1, 18.2, 18.3_
  
  - [ ] 8.7 Write unit tests for experiment runner
    - Test run schedule generation (verify 34 runs)
    - Test condition switching (mock K8s API)
    - Test snapshot construction
    - Mock load generator and Prometheus queries
    - _Requirements: 6.1, 6.3, 6.4, 7.3_

- [ ] 9. Complete results analyzer implementation
  - [x] 9.1 Implement per-run summarization
    - Read JSONL snapshot files from experiments/results directory
    - Calculate SLO violation rate (fraction of intervals where front-end p95 > 36ms)
    - Calculate total replica-seconds (sum of replicas × 30s across all services)
    - Calculate mean replicas and peak replicas
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 9.2 Implement aggregation by condition and pattern
    - Group runs by condition (proactive vs reactive)
    - Group runs by pattern (constant, step, spike, ramp)
    - Calculate mean and standard deviation for each metric
    - _Requirements: 8.4_
  
  - [x] 9.3 Implement statistical comparison
    - Apply Mann-Whitney U test for each metric × pattern combination
    - Compare proactive vs reactive conditions
    - Calculate U statistic and p-value
    - Mark results as significant when p < 0.05
    - _Requirements: 8.5, 19.3_
  
  - [x] 9.4 Implement CSV output generation
    - Generate summary.csv with per-run metrics
    - Generate statistics.csv with Mann-Whitney test results
    - Include columns specified in requirements
    - _Requirements: 8.6, 8.7, 19.1, 19.2_
  
  - [x] 9.5 Implement console table output
    - Format results table for inclusion in research paper
    - Display proactive vs reactive comparison
    - Highlight significant differences
    - _Requirements: 19.4_
  
  - [ ] 9.6 Write unit tests for results analyzer
    - Test per-run metric calculation with sample data
    - Test aggregation logic
    - Test Mann-Whitney U test computation
    - Test CSV generation
    - _Requirements: 8.2, 8.3, 8.5_

### Phase 7: GKE Deployment and Validation

- [ ] 10. Deploy system to GKE
  - [x] 10.1 Verify GKE cluster configuration
    - Verify cluster exists in us-central1 region
    - Verify node pool has 3× e2-standard-4 nodes
    - Verify sock-shop namespace exists
    - Verify all 7 monitored services are deployed
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [x] 10.2 Deploy Kafka infrastructure
    - Apply Kafka broker and Zookeeper manifests
    - Verify Kafka topics created: metrics, model-votes, scaling-decisions
    - Test Kafka connectivity from services
    - _Requirements: 12.1_
  
  - [x] 10.3 Deploy system services
    - Deploy metrics aggregator
    - Deploy 3 ML inference services (LR, RF, XGB)
    - Deploy authoritative scaler
    - Deploy scaling controller (initially scaled to 0)
    - Verify all pods are running
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  
  - [x] 10.4 Configure environment variables
    - Set KAFKA_BOOTSTRAP_SERVERS for all services
    - Set MODEL_PATH for ML inference services
    - Set NAMESPACE, SLO_THRESHOLD_MS, COOLDOWN_MINUTES for scaling controller
    - Set SCALE_EVENT_LOG path for scaling controller
    - Verify configuration with default values documented
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 20.1_

- [ ] 11. Run smoke tests on GKE
  - [x] 11.1 Test proactive condition
    - Enable proactive condition (delete HPA, scale controller to 1)
    - Generate constant load for 5 minutes
    - Verify metrics flow through Kafka pipeline
    - Verify scaling decisions are made
    - Verify replica counts change in response to load
    - Check scaling event log for entries
    - _Requirements: 1.1, 1.2, 2.1, 2.5, 5.1_
  
  - [x] 11.2 Test reactive condition
    - Enable reactive condition (apply HPA, scale controller to 0)
    - Generate constant load for 5 minutes
    - Verify HPA scales services based on CPU
    - Verify scaling controller is not running
    - _Requirements: 10.4, 10.5_
  
  - [x] 11.3 Test condition switching
    - Switch from proactive to reactive
    - Verify HPA applied and controller stopped
    - Switch from reactive to proactive
    - Verify HPA deleted and controller started
    - _Requirements: 6.3, 6.4, 10.4, 10.5_
  
  - [x] 11.4 Test load generator patterns
    - Run constant pattern and verify steady load
    - Run step pattern and verify load increases in steps
    - Run spike pattern and verify sudden load spikes
    - Run ramp pattern and verify gradual load increase
    - _Requirements: 6.5_

- [x] 12. Checkpoint - Validate system readiness
  - Review smoke test results
  - Verify all 7 services are monitored correctly
  - Verify metrics collection captures all required data
  - Verify scaling events are logged correctly
  - Verify load generator produces expected patterns
  - Ensure all tests pass, ask the user if questions arise.

### Phase 8: Experiment Execution and Analysis

- [x] 13. PAUSE POINT - Prepare for overnight experiment run
  - Review experiment configuration in run_config.py
  - Verify 34-run schedule is correct
  - Verify estimated time (~8.5 hours) is acceptable
  - Verify results directory is empty or backed up
  - Verify GKE cluster has sufficient resources
  - Verify no manual interventions will be needed
  - **USER CONFIRMATION REQUIRED BEFORE PROCEEDING**

- [ ] 14. Execute full experiment suite
  - [x] 14.1 Run experiment runner with pause flag
    - Execute: `python experiments/run_experiments.py --pause-before-start`
    - Review printed run schedule
    - Confirm to start experiments
    - _Requirements: 18.1, 18.2_
  
  - [x] 14.2 Monitor experiment execution
    - Check logs periodically for errors
    - Verify JSONL files are being created
    - Verify no services are crashing
    - _Requirements: 6.8, 12.2_
  
  - [ ] 14.3 Verify experiment completion
    - Verify all 34 JSONL files exist in experiments/results
    - Verify each file has 24 snapshot entries
    - Check for any error logs or incomplete runs
    - _Requirements: 6.8, 7.3_

- [ ] 15. Analyze experiment results
  - [ ] 15.1 Run results analyzer
    - Execute: `python experiments/analyse_results.py`
    - Verify summary.csv is generated
    - Verify statistics.csv is generated
    - Review console table output
    - _Requirements: 8.6, 8.7, 19.1, 19.2, 19.4_
  
  - [ ] 15.2 Validate results
    - Check for missing data or anomalies
    - Verify SLO violation rates are reasonable
    - Verify replica counts are within bounds (1-10)
    - Verify statistical tests ran successfully
    - _Requirements: 8.2, 8.3, 8.5, 19.3_
  
  - [ ] 15.3 Generate final results for paper
    - Extract key findings from statistics.csv
    - Format comparison table for paper
    - Document significant differences (p < 0.05)
    - Calculate improvement percentages (proactive vs reactive)
    - _Requirements: 19.3, 19.4_

- [ ] 16. Final checkpoint - Document findings
  - Summarize SLO violation rate comparison
  - Summarize resource efficiency comparison
  - Document any unexpected behaviors or insights
  - Prepare results section for graduation paper
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure validation at key milestones
- The pause point before Phase 8 is critical - do not proceed without user confirmation
- Use existing virtual environment at `kafka-structured/services/metrics-aggregator/venv/`
- Model files are at `ML-Models/gke/models_mixed_standard/model_{lr,rf,xgb}.joblib`
- Total experiment time is approximately 8.5 hours (34 runs × 15 minutes)
- System must run on GKE to compare against HPA baseline
