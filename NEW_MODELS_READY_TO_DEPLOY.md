# New ML Models Ready to Deploy

## Status: READY ✅

The Docker image with your new models has been built and pushed to GCR.

## What's Been Prepared

### 1. Docker Image Built
- **Image**: `gcr.io/grad-phca/ml-inference:latest`
- **Digest**: `sha256:df5c63ae353ef1912f557fbae77d55db6b09eab9e4fe8a6e6172da2c4492adad`
- **Size**: 1.74GB
- **Status**: Pushed to Google Container Registry

### 2. Models Included

| Model | Type | Path in Container | Source File |
|-------|------|-------------------|-------------|
| Logistic Regression | One-hot encoded | `/models/models_mixed_onehot_lr/model.joblib` | `model_lr.joblib` |
| Random Forest | One-hot encoded | `/models/models_mixed_onehot_rf/model.joblib` | `model_rf.joblib` |
| SVM | One-hot encoded | `/models/models_additional/model.joblib` | `model_svm.joblib` |

### 3. Deployment Files Updated

- ✅ `kafka-structured/k8s/ml-inference-lr-deployment.yaml` - Updated to use new LR model
- ✅ `kafka-structured/k8s/ml-inference-rf-deployment.yaml` - Updated to use new RF model
- ✅ `kafka-structured/k8s/ml-inference-xgb-deployment.yaml` - Updated to use SVM model (renamed from XGBoost)

### 4. Model Names

The authoritative scaler expects 3 models. The new configuration:
- `logistic_regression` (LR with one-hot encoding)
- `random_forest` (RF with one-hot encoding)
- `svm` (SVM with one-hot encoding, replaces XGBoost)

## Deployment Commands (Run AFTER Experiment Finishes)

```bash
# Switch to pipeline cluster
kubectl config use-context gke_grad-phca_us-central1-a_pipeline-cluster

# Apply updated deployments
kubectl apply -f kafka-structured/k8s/ml-inference-lr-deployment.yaml
kubectl apply -f kafka-structured/k8s/ml-inference-rf-deployment.yaml
kubectl apply -f kafka-structured/k8s/ml-inference-xgb-deployment.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=ml-inference-lr -n kafka --timeout=2m
kubectl wait --for=condition=ready pod -l app=ml-inference-rf -n kafka --timeout=2m
kubectl wait --for=condition=ready pod -l app=ml-inference-svm -n kafka --timeout=2m

# Verify pods are running
kubectl get pods -n kafka | grep ml-inference

# Switch back to sock-shop cluster
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster
```

## What Changed

### Before (Old Models)
- LR: Trained on original dataset
- RF: Trained on original dataset  
- XGBoost: Trained on original dataset
- Service feature: Single categorical feature

### After (New Models)
- LR: Trained on new dataset with one-hot encoding
- RF: Trained on new dataset with one-hot encoding
- SVM: Trained on new dataset with one-hot encoding (replaces XGBoost)
- Service feature: One-hot encoded (7 services: carts, catalogue, front-end, orders, payment, shipping, user)

## Expected Behavior After Deployment

### ML Inference Services
- Each service will load its new model on startup
- Models will make predictions using one-hot encoded service features
- Predictions should be more accurate due to better feature engineering

### Inference Code
The `inference.py` already has one-hot encoding implemented:
```python
# One-hot encode service name (7 services)
service_encoded = [0] * 7
service_map = {
    'carts': 0, 'catalogue': 1, 'front-end': 2,
    'orders': 3, 'payment': 4, 'shipping': 5, 'user': 6
}
if service_name in service_map:
    service_encoded[service_map[service_name]] = 1
```

### Authoritative Scaler
- Will receive votes from LR, RF, and SVM
- Aggregates votes using majority voting
- Makes scaling decisions based on consensus

## Validation After Deployment

Run a proactive test to verify:
```bash
python kafka-structured/experiments/run_single_test.py --condition proactive --pattern step --run-id 992
```

**Expected results**:
- All 3 ML models vote on each service
- Scaling decisions are made based on votes
- System responds to violations
- No errors in ML inference pod logs

## Rollback Plan (If Needed)

If new models don't work:
```bash
# Revert to old model paths
kubectl set env deployment/ml-inference-lr -n kafka MODEL_PATH=/models/lr
kubectl set env deployment/ml-inference-rf -n kafka MODEL_PATH=/models/rf
kubectl set env deployment/ml-inference-xgb -n kafka MODEL_PATH=/models/xgb MODEL_NAME=xgboost
```

## Notes

- The Docker image contains BOTH old and new models for easy rollback
- Old models are at: `/models/lr/`, `/models/rf/`, `/models/xgb/`
- New models are at: `/models/models_mixed_onehot_lr/`, `/models/models_mixed_onehot_rf/`, `/models/models_additional/`
- Switching between them is just changing the MODEL_PATH environment variable

## Timeline

1. ✅ **DONE**: Docker image built and pushed
2. ✅ **DONE**: Deployment files updated
3. ⏳ **WAITING**: Current experiment to finish
4. ⏳ **TODO**: Apply deployments (5 minutes)
5. ⏳ **TODO**: Run validation test (12 minutes)
6. ⏳ **TODO**: Verify results and proceed

**Total time after experiment**: ~20 minutes to deploy and validate
