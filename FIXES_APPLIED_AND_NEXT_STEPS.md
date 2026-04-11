# FIXES APPLIED AND NEXT STEPS

## ✅ FIXES COMPLETED

### 1. Updated ML Inference Service ✅
- **File**: `kafka-structured/services/ml-inference/inference.py`
- **Change**: Added one-hot encoding for service feature
- **Services**: carts, catalogue, front-end, orders, payment, shipping, user
- **Impact**: Now compatible with new models trained on one-hot encoded data

### 2. Fixed Prometheus URL ✅
- **File**: `kafka-structured/experiments/run_experiments.py`
- **Change**: Default URL changed from internal cluster DNS to external IP
- **Old**: `http://prometheus-server.sock-shop.svc.cluster.local:9090`
- **New**: `http://34.170.213.190:9090`
- **Impact**: Experiments can now query Prometheus from local machine

### 3. Fixed Locust Timeout ✅
- **File**: `locustfile_step.py` on Locust VM
- **Change**: Timeout increased from 2s to 10s
- **Impact**: Should reduce failure rate from 84% to <10%

---

## 🔄 NEXT STEPS REQUIRED

### Step 1: Update Model Paths in Deployments

Need to update 3 deployment files to point to new models:

#### A. Logistic Regression
**File**: `kafka-structured/k8s/ml-inference-lr-deployment.yaml`
**Change**: Update MODEL_PATH
```yaml
- name: MODEL_PATH
  value: "/models/models_mixed_onehot/model_lr.joblib"
```

#### B. Random Forest
**File**: `kafka-structured/k8s/ml-inference-rf-deployment.yaml`
**Change**: Update MODEL_PATH
```yaml
- name: MODEL_PATH
  value: "/models/models_mixed_onehot/model_rf.joblib"
```

#### C. SVM (rename from XGBoost)
**File**: `kafka-structured/k8s/ml-inference-xgb-deployment.yaml` → rename to `ml-inference-svm-deployment.yaml`
**Changes**:
1. Rename file
2. Update all references from "xgb" to "svm"
3. Update MODEL_PATH to `/models/models_additional/model_svm.joblib`
4. Update image name to `gcr.io/grad-phca/ml-inference-svm:latest`

### Step 2: Update Authoritative Scaler

**File**: `kafka-structured/services/authoritative-scaler/scaler.py`
**Change**: Update expected model names from ["logistic_regression", "random_forest", "xgboost"] to ["logistic_regression", "random_forest", "svm"]

### Step 3: Build and Push Docker Images

Need to build 3 new images with updated inference code:

```bash
cd kafka-structured/services/ml-inference

# Build LR image
gcloud builds submit --config=cloudbuild-lr.yaml --substitutions=_MODEL_PATH=models_mixed_onehot/model_lr.joblib

# Build RF image  
gcloud builds submit --config=cloudbuild-rf.yaml --substitutions=_MODEL_PATH=models_mixed_onehot/model_rf.joblib

# Build SVM image (new)
gcloud builds submit --config=cloudbuild-svm.yaml --substitutions=_MODEL_PATH=models_additional/model_svm.joblib
```

### Step 4: Deploy Updated Services

```bash
# Apply updated deployments
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster apply -f kafka-structured/k8s/ml-inference-lr-deployment.yaml
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster apply -f kafka-structured/k8s/ml-inference-rf-deployment.yaml
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster apply -f kafka-structured/k8s/ml-inference-svm-deployment.yaml

# Delete old XGBoost deployment
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster delete deployment ml-inference-xgb -n kafka

# Apply updated authoritative scaler
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster rollout restart deployment/authoritative-scaler -n kafka
```

### Step 5: Verify Deployment

```bash
# Check all ML inference pods are running
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep ml-inference

# Check logs for successful model loading
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-lr --tail=20
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-rf --tail=20
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-svm --tail=20

# Check authoritative scaler logs
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=50
```

### Step 6: Run Validation Test

```bash
# Run single proactive test
kafka-structured\services\metrics-aggregator\venv\Scripts\python.exe kafka-structured\experiments\run_single_test.py --condition proactive --pattern step --run-id 995

# Verify:
# - Models voting correctly (LR, RF, SVM)
# - Scaling happening
# - Locust success rate >90%
# - No Prometheus errors
```

---

## ⚠️ IMPORTANT NOTES

### Model File Locations
- **LR**: `kafka-structured/ML-Models/gke/models_mixed_onehot/model_lr.joblib`
- **RF**: `kafka-structured/ML-Models/gke/models_mixed_onehot/model_rf.joblib`
- **SVM**: `kafka-structured/ML-Models/gke/models_additional/model_svm.joblib`

### Cloud Build Files
Need to check if cloudbuild YAML files exist for each model. If not, need to create them.

### Docker Images
Current images in GCR:
- `gcr.io/grad-phca/ml-inference-lr:latest`
- `gcr.io/grad-phca/ml-inference-rf:latest`
- `gcr.io/grad-phca/ml-inference-xgb:latest` (will be replaced by svm)

---

## 📋 CHECKLIST

- [x] Update inference.py with one-hot encoding
- [x] Fix Prometheus URL in run_experiments.py
- [x] Fix Locust timeout on VM
- [ ] Update ml-inference-lr-deployment.yaml
- [ ] Update ml-inference-rf-deployment.yaml
- [ ] Create ml-inference-svm-deployment.yaml
- [ ] Update authoritative-scaler/scaler.py
- [ ] Check/create Cloud Build configs
- [ ] Build and push Docker images
- [ ] Deploy updated services
- [ ] Verify deployment
- [ ] Run validation test

---

## ESTIMATED TIME REMAINING
- Deployment updates: 15 minutes
- Docker builds: 15 minutes
- Deployment and verification: 15 minutes
- Validation test: 15 minutes
- **Total: ~1 hour**

---

## READY TO PROCEED?

Please confirm you want me to:
1. Update the deployment YAMLs
2. Update the authoritative scaler
3. Check for Cloud Build configs
4. Proceed with builds and deployment

Or let me know if you want to review/modify anything first.
