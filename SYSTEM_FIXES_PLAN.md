# SYSTEM FIXES BEFORE FINAL EXPERIMENTS

## ISSUES IDENTIFIED

### 1. Wrong ML Models
- Current: LR, RF, XGBoost
- New: LR, RF, SVM
- Models trained on one-hot encoded service features

### 2. Prometheus URL Issue
- Script uses internal cluster DNS: `prometheus-server.sock-shop.svc.cluster.local`
- Should use external IP: `34.170.213.190:9090`
- Need to set PROMETHEUS_URL environment variable

### 3. Locust Timeout Issue
- Current timeout: 2 seconds
- Causing 84% failure rate when services are slow
- Need to increase timeout or accept as design

---

## FIX 1: UPDATE ML MODELS

### New Model Locations:
- **RandomForest**: `kafka-structured/ML-Models/gke/models_mixed_onehot/model_rf.joblib`
- **SVM**: `kafka-structured/ML-Models/gke/models_additional/model_svm.joblib`
- **Logistic Regression**: `kafka-structured/ML-Models/gke/models_mixed_onehot/model_lr.joblib`

### Changes Needed:

#### 1.1 Update ML Inference Deployments
Files to update:
- `kafka-structured/k8s/ml-inference-lr-deployment.yaml`
- `kafka-structured/k8s/ml-inference-rf-deployment.yaml`
- `kafka-structured/k8s/ml-inference-xgb-deployment.yaml` → rename to `ml-inference-svm-deployment.yaml`

Change model paths in volume mounts and MODEL_PATH env vars.

#### 1.2 Update ML Inference Service Code
Check if the inference code needs updates for:
- One-hot encoded service features
- SVM instead of XGBoost

#### 1.3 Rebuild and Push Docker Images
```bash
# Build new images with updated models
cd kafka-structured/services/ml-inference
docker build -t gcr.io/grad-phca/ml-inference-lr:latest -f Dockerfile.lr .
docker build -t gcr.io/grad-phca/ml-inference-rf:latest -f Dockerfile.rf .
docker build -t gcr.io/grad-phca/ml-inference-svm:latest -f Dockerfile.svm .

# Push to GCR
docker push gcr.io/grad-phca/ml-inference-lr:latest
docker push gcr.io/grad-phca/ml-inference-rf:latest
docker push gcr.io/grad-phca/ml-inference-svm:latest
```

#### 1.4 Update Authoritative Scaler
Update to expect 3 models: LR, RF, SVM (not XGB)

---

## FIX 2: PROMETHEUS URL

### Option A: Set Environment Variable (Quick Fix)
```bash
export PROMETHEUS_URL="http://34.170.213.190:9090"
```

### Option B: Update Default in Code (Permanent Fix)
Update `kafka-structured/experiments/run_experiments.py` line 28:
```python
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://34.170.213.190:9090")
```

**Recommendation**: Use Option B (permanent fix)

---

## FIX 3: LOCUST TIMEOUT

### Current Issue:
- Timeout: 2 seconds
- Services at 1 replica respond slowly (>2s)
- Locust marks as failure
- Creates unfair comparison

### Options:

#### Option A: Increase Timeout (Recommended)
Update `locustfile_step.py` on VM:
```python
timeout = 10  # Increase from 2 to 10 seconds
```

**Pros**: Fair comparison, both tests get same load
**Cons**: Deviates from EuroSys paper methodology

#### Option B: Accept Current Behavior
Keep 2-second timeout as per paper.

**Pros**: Follows paper methodology
**Cons**: Unfair comparison (proactive gets more load due to faster responses)

#### Option C: Pre-scale Reactive Baseline
Start reactive test with 2 replicas instead of 1.

**Pros**: Fair starting point
**Cons**: Not a true baseline comparison

**Recommendation**: Option A (increase timeout to 10s)

---

## EXECUTION PLAN

### Phase 1: Check Model Feature Requirements (15 min)
1. Read new model training code to understand one-hot encoding
2. Check if inference service needs updates
3. Verify feature vector construction

### Phase 2: Update ML Pipeline (30 min)
1. Update deployment YAMLs with new model paths
2. Update inference service code if needed
3. Build and push new Docker images
4. Deploy updated services to GKE
5. Verify models load correctly

### Phase 3: Fix Prometheus URL (5 min)
1. Update default in run_experiments.py
2. Test connection from local machine

### Phase 4: Fix Locust Timeout (10 min)
1. SSH to Locust VM
2. Update locustfile_step.py timeout to 10s
3. Test with manual run
4. Verify failure rate drops

### Phase 5: Validation Test (30 min)
1. Run single proactive test
2. Verify:
   - Models voting correctly
   - Scaling happening
   - Locust success rate >90%
   - Prometheus queries working
3. Run single reactive test
4. Compare results

### Phase 6: Full Experiments (7+ hours)
1. Run mini-suite (8 runs, 1.6 hours)
2. If successful, run full suite (34 runs, 7.1 hours)

---

## TOTAL ESTIMATED TIME
- Fixes: 1 hour
- Validation: 30 minutes
- Mini-suite: 1.6 hours
- Full suite: 7.1 hours
- **Total: ~10 hours**

---

## NEXT IMMEDIATE ACTIONS

1. ✅ Check if inference service needs updates for one-hot encoding
2. ✅ Update model paths in deployments
3. ✅ Fix Prometheus URL
4. ✅ Fix Locust timeout
5. ✅ Run validation test
