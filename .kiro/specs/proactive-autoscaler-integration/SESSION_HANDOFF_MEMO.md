# Session Handoff Memo - Proactive Autoscaler Integration

**Date:** 2026-04-10  
**Session Token Usage:** 45k/200k (23%) - NEW SESSION  
**Spec:** proactive-autoscaler-integration (feature, design-first workflow)  
**Status:** Phase 7 in progress - Deploying Kafka to pipeline cluster (Task 10.2)

---

## CRITICAL CONTEXT

### Two-Cluster Architecture (IMPORTANT!)

**We use SEPARATE clusters for clean methodology:**

**sock-shop-cluster (Application):**
- 3× e2-standard-4 nodes (12 vCPUs, 48 GB RAM)
- Master IP: 34.66.13.244
- Zone: us-central1-a
- Cost: $0.40/hour
- **Deployed:** Sock Shop (7 services) + Prometheus
- **External IPs:**
  - front-end: 104.154.246.88
  - prometheus: 34.170.213.190:9090

**pipeline-cluster (Control Plane):**
- 2× e2-standard-2 nodes (4 vCPUs, 16 GB RAM)
- Master IP: 136.115.218.105
- Zone: us-central1-a
- Cost: $0.13/hour
- **Deployed:** Nothing yet (ready for Kafka + pipeline services)

**Total Cost:** $0.53/hour ($4.50 for 8.5-hour experiment)

### Why Separate Clusters?

**Methodological soundness:**
- Pipeline overhead doesn't affect Sock Shop metrics
- Both conditions (proactive/reactive) see identical Sock Shop environment
- Preserves existing SLO threshold (36ms)
- No need to recalibrate or retrain models
- Publishable methodology

### Model Configuration (CRITICAL!)
**USE MODELS WITHOUT SERVICE FEATURE:**
- Path: `ML-Models/gke/experiment_no_service/models/`
- Files:
  - `model_lr_gke_mixed.joblib` (Logistic Regression)
  - `model_rf_gke_mixed.joblib` (Random Forest)
  - `model_xgb_gke_mixed.joblib` (XGBoost)

---

## COMPLETED TASKS (23/44)

### Phase 1-5: Previous Session ✅
- [x] Tasks 1-7.2: All previous work (see old memo for details)
- Key fixes: Decision format (SCALE_UP/NO_OP), RBAC (Role/RoleBinding), Model paths

### Phase 6: Experiment Tooling ✅
- [x] Task 8.1: Run schedule generation
- [x] Task 8.2: Condition switching (enable_proactive, enable_reactive, reset_cluster)
- [x] Task 8.3: Metrics collection (Prometheus queries for p95, CPU)
- [x] Task 8.4: Run execution loop (12 min load + 3 min settle)
- [x] Task 8.5: Validation checks (services, controller, Prometheus, Locust VM)
- [x] Task 8.6: Pause-before-start flag
- [x] Task 9.1: Per-run summarization
- [x] Task 9.2: Aggregation by condition/pattern
- [x] Task 9.3: Statistical comparison (Mann-Whitney U)
- [x] Task 9.4: CSV output (summary.csv, statistics.csv)
- [x] Task 9.5: Console table output (research paper format)
- [x] **BONUS:** Locust VM integration via SSH

### Phase 7: GKE Deployment (1/8 tasks) ✅
- [x] Task 10.1: Verified GKE cluster configuration
  - Created sock-shop-cluster (3 nodes)
  - Created pipeline-cluster (2 nodes)
  - Verified Sock Shop deployment (all 7 services)
  - Exposed Prometheus via LoadBalancer

---

## CURRENT TASK

**Task 10.2: Deploy Kafka infrastructure to pipeline-cluster**

**What needs to be done:**
1. Switch to pipeline-cluster context
2. Create kafka namespace (or use default)
3. Deploy Zookeeper
4. Deploy Kafka broker
5. Create topics: metrics, model-votes, scaling-decisions
6. Test connectivity

**Files ready:**
- Need to create Kafka manifests or use Helm chart

---

## REMAINING TASKS (21/44)

### Phase 7: GKE Deployment (7 remaining)
- [ ] 10.2: Deploy Kafka infrastructure ← **NEXT TASK**
- [ ] 10.3: Deploy system services
- [ ] 10.4: Configure environment variables
- [ ] 11.1: Test proactive condition
- [ ] 11.2: Test reactive condition
- [ ] 11.3: Test condition switching
- [ ] 11.4: Test load generator patterns
- [ ] 12: Checkpoint - Validate system readiness

### Phase 8: Experiment Execution (5 tasks)
- [ ] 13: PAUSE POINT - Prepare for overnight run
- [ ] 14.1-14.3: Execute full experiment suite (34 runs, ~8.5 hours)
- [ ] 15.1-15.3: Analyze results
- [ ] 16: Final checkpoint

---

## KEY FILES CREATED THIS SESSION

### Experiment Runner & Analyzer
1. `kafka-structured/experiments/run_experiments.py` ✅
   - Condition switching functions
   - Metrics collection with Prometheus queries
   - Locust VM integration via SSH
   - Validation checks
   - Pause-before-start flag

2. `kafka-structured/experiments/analyse_results.py` ✅
   - Per-run summarization
   - Statistical comparison (Mann-Whitney U)
   - CSV output generation
   - Console table output

3. `kafka-structured/experiments/run_config.py` ✅
   - 34-run schedule generation
   - Configuration constants

### Kubernetes Manifests
4. `kafka-structured/k8s/prometheus-external-service.yaml` ✅
   - LoadBalancer service to expose Prometheus
   - Accessible at 34.170.213.190:9090

### Documentation
5. `kafka-structured/CLUSTER_ARCHITECTURE.md` ✅
   - Two-cluster architecture explanation
   - Network configuration
   - Methodological benefits

6. `kafka-structured/DEPLOYMENT_PROGRESS.md` ✅
   - Current deployment status
   - Configuration details
   - Cost tracking

7. `kafka-structured/IMPLEMENTATION_STATUS.md` ✅
   - Overall progress (23/44 tasks)
   - What's ready to use

8. `kafka-structured/experiments/LOCUST_INTEGRATION_COMPLETE.md` ✅
   - Locust VM integration details
   - SSH configuration
   - Troubleshooting

9. `kafka-structured/experiments/TASKS_8_9_COMPLETE.md` ✅
   - Experiment tooling completion details

---

## IMPORTANT DECISIONS & FIXES

### 1. Two-Cluster Architecture
**Decision:** Use separate clusters for Sock Shop and pipeline
**Reason:** Prevents pipeline overhead from affecting Sock Shop metrics
**Impact:** Clean methodology, fair comparison, publishable results
**Cost:** Extra $1.10 for 8.5-hour experiment (26% increase)

### 2. Pipeline Cluster Size
**Decision:** 2× e2-standard-2 nodes (not e2-medium)
**Reason:** e2-medium has only 4 GB RAM per node (too tight for pipeline)
**Resources:** 4 vCPUs, 16 GB RAM total (sufficient for pipeline)

### 3. Standard Disks for Pipeline
**Decision:** Use pd-standard instead of SSD
**Reason:** Hit SSD quota limit (500 GB in us-central1)
**Impact:** None (pipeline is CPU/RAM intensive, not disk I/O)

### 4. Prometheus Exposure
**Decision:** Expose via LoadBalancer (not NodePort)
**Reason:** Simpler for cross-cluster access
**URL:** http://34.170.213.190:9090

---

## CONFIGURATION SUMMARY

### Locust VM
- Name: locust-runner
- IP: 136.115.51.98
- SSH User: User
- SSH Key: ~/.ssh/google_compute_engine
- Locustfiles: ~/locustfile_{constant,step,spike,ramp}.py
- Virtual env: ~/locust-venv

### Sock Shop
- External IP: 104.154.246.88
- Services: front-end, carts, orders, catalogue, user, payment, shipping
- All at 1 replica initially
- Scale range: 1-10 replicas

### Prometheus
- External URL: http://34.170.213.190:9090
- Namespace: monitoring (in sock-shop-cluster)
- Service: prometheus-server-external (LoadBalancer)

### Scaling Controller Config
- SLO_THRESHOLD_MS: 36.0
- COOLDOWN_MINUTES: 5
- MIN_REPLICAS: 1
- MAX_REPLICAS: 10
- SCALEDOWN_CPU_PCT: 30.0
- SCALEDOWN_LAT_RATIO: 0.7
- SCALEDOWN_WINDOW: 10

### Experiment Schedule
- Total runs: 34
- Conditions: 2 (proactive, reactive)
- Patterns: 4 (constant, step, spike, ramp)
- Repetitions: constant=2, step=5, spike=5, ramp=5
- Duration per run: 15 minutes
- Total time: ~8.5 hours

---

## KUBECTL CONTEXTS

**Switch between clusters:**

```bash
# Sock Shop cluster
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster

# Pipeline cluster
kubectl config use-context gke_grad-phca_us-central1-a_pipeline-cluster

# List contexts
kubectl config get-contexts
```

---

## NEXT STEPS FOR NEW SESSION

### Immediate Actions (Task 10.2)

1. **Switch to pipeline-cluster**
   ```bash
   kubectl config use-context gke_grad-phca_us-central1-a_pipeline-cluster
   ```

2. **Deploy Kafka using Helm or manifests**
   
   **Option A: Helm (RECOMMENDED)**
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm install kafka bitnami/kafka --namespace kafka --create-namespace \
     --set replicaCount=1 \
     --set zookeeper.replicaCount=1 \
     --set resources.requests.memory=1Gi \
     --set resources.requests.cpu=500m
   ```

   **Option B: Simple manifests**
   - Create Zookeeper deployment + service
   - Create Kafka deployment + service
   - Keep it minimal (1 replica each)

3. **Create Kafka topics**
   ```bash
   kubectl exec -it kafka-0 -n kafka -- kafka-topics.sh \
     --create --topic metrics --bootstrap-server localhost:9092
   kubectl exec -it kafka-0 -n kafka -- kafka-topics.sh \
     --create --topic model-votes --bootstrap-server localhost:9092
   kubectl exec -it kafka-0 -n kafka -- kafka-topics.sh \
     --create --topic scaling-decisions --bootstrap-server localhost:9092
   ```

4. **Test Kafka connectivity**
   ```bash
   kubectl exec -it kafka-0 -n kafka -- kafka-topics.sh \
     --list --bootstrap-server localhost:9092
   ```

### After Task 10.2

- **Task 10.3:** Deploy pipeline services
  - Metrics aggregator (set PROMETHEUS_URL=http://34.170.213.190:9090)
  - ML inference (3 pods with models)
  - Authoritative scaler
  - Scaling controller (needs kubeconfig for sock-shop-cluster)

- **Task 10.4:** Configure environment variables
  - PROMETHEUS_URL for metrics aggregator
  - KAFKA_BOOTSTRAP_SERVERS for all services
  - MODEL_PATH for ML inference
  - Kubeconfig for scaling controller

---

## KNOWN ISSUES & NOTES

### Issue: Prometheus LoadBalancer Connection
**Status:** External IP assigned (34.170.213.190) but connection may be refused initially
**Possible causes:** Firewall rule needed, or propagation delay
**Workaround:** Can use kubectl port-forward if needed
**Test:** `curl http://34.170.213.190:9090/api/v1/query?query=up`

### Note: SSD Quota
- Hit 500 GB SSD quota in us-central1
- Pipeline cluster uses standard disks (pd-standard)
- No performance impact for our use case

### Note: Virtual Environment
- Use existing venv: `kafka-structured/services/metrics-aggregator/venv/`
- All Python dependencies already installed

---

## TESTING STATUS

### Unit Tests: ✅ All Passing
- Kafka pipeline: 8/8
- DecisionsKafkaProducer: 9/9
- Decision loop: 3/3
- Scale-up logic: 6/6
- Scale-down logic: 9/9

### Integration Tests: ✅ Ready
- Condition switching test script created
- Experiment runner syntax validated
- Results analyzer syntax validated

### Smoke Tests: ⏳ Pending
- Need to complete deployment first
- Then run Tasks 11.1-11.4

---

## QUESTIONS TO ASK USER (if needed)

1. Prefer Helm or simple manifests for Kafka?
2. Any specific Kafka configuration requirements?
3. Should we test Prometheus connectivity before proceeding?

---

## TOKEN USAGE TRACKING

- **Current Session:** 135k/200k (68%)
- **Recommended Handoff:** When approaching 180k tokens
- **This memo created at:** 135k tokens

---

## SPEC REFERENCE

- **Spec Path:** `.kiro/specs/proactive-autoscaler-integration/`
- **Spec Type:** Feature (design-first workflow)
- **Requirements:** `requirements.md`
- **Design:** `design.md`
- **Tasks:** `tasks.md`

---

**END OF MEMO**

**Next session should start with:** "Continue from Task 10.2: Deploy Kafka infrastructure to pipeline-cluster"

**Key command to run first:**
```bash
kubectl config use-context gke_grad-phca_us-central1-a_pipeline-cluster
```

