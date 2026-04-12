# Debug RPS Gate Issue

## Problem
All 3 ML models are voting NO_ACTION with 100% confidence, causing the proactive system to never scale. We suspect the RPS gate is blocking all predictions.

## What We Changed
Added debug logging to `kafka-structured/services/ml-inference/inference.py`:
- Logs RPS value for every prediction
- Logs when RPS gate blocks a prediction
- Logs actual model predictions when they run

## Steps to Debug

### 1. Rebuild and Deploy ML Inference Services
```powershell
cd kafka-structured/services/ml-inference
.\rebuild_and_deploy.ps1
```

This will:
- Build new Docker image using Google Cloud Build (no local Docker needed)
- Push to Google Container Registry
- Update all 3 ML inference deployments (xgb, rf, lr)
- Wait for rollout to complete (~3-4 minutes)

### 2. Run Quick Test
```powershell
cd kafka-structured/experiments
.\quick_test.ps1 -Condition proactive
```

This will:
- Configure proactive mode (delete HPAs, start scaling-controller)
- Reset all services to 1 replica
- Start 5-minute constant load test (150 users)
- Show live ML inference logs with RPS values

### 3. Analyze the Logs

Look for these patterns in the output:

**Pattern A: RPS Gate is Blocking (BAD)**
```
[RPS CHECK] front-end: RPS=0.50, threshold=1.0
[RPS GATE BLOCKED] front-end: RPS 0.50 < 1.0, returning NO_OP
```
This means the metrics aggregator is publishing RPS < 1.0, which is wrong during a load test.

**Pattern B: RPS is Good, Models Predict (GOOD)**
```
[RPS CHECK] front-end: RPS=45.23, threshold=1.0
[PREDICTION] front-end: SCALE_UP (confidence=95.23%, RPS=45.23)
```
This means RPS values are correct and models are making predictions.

**Pattern C: RPS is Good, Models Predict NO_OP (CONCERNING)**
```
[RPS CHECK] front-end: RPS=45.23, threshold=1.0
[PREDICTION] front-end: NO_OP (confidence=87.45%, RPS=45.23)
```
This means models are genuinely predicting NO_OP despite high load (training/testing mismatch).

## Expected Results

### If RPS Gate is the Problem
- You'll see RPS < 1.0 for all services
- All predictions will be blocked
- Fix: Debug metrics aggregator RPS calculation

### If Models Don't Generalize to 150 Users
- You'll see RPS > 1.0 but models predict NO_OP
- Models trained on 50 users, tested on 150 users
- Fix: Either test with 50 users or retrain with 150-user data

### If Everything Works
- You'll see RPS > 1.0
- Models predict SCALE_UP for services with high latency
- Authoritative scaler makes SCALE_UP decisions
- Services actually scale

## Additional Debugging

### Check Authoritative Scaler Decisions
```powershell
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=50
```

Look for:
```
SCALING DECISION #XXXXX @ 2026-04-12 XX:XX:XX UTC
Service: front-end
  random_forest        -> SCALE UP   (confidence: 95.00%)
  logistic_regression  -> SCALE UP   (confidence: 92.00%)
  svm                  -> SCALE UP   (confidence: 88.00%)
DECISION: SCALE_UP
```

### Check Metrics Aggregator
```powershell
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/metrics-aggregator --tail=50
```

### Check Scaling Controller
```powershell
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=50
```

### Verify HPAs are Deleted (Proactive Mode)
```powershell
kubectl get hpa -n sock-shop
```
Should return: `No resources found in sock-shop namespace.`

If HPAs exist, delete them manually:
```powershell
kubectl delete hpa --all -n sock-shop
```

## Rollback

If you need to rollback to the previous image:
```powershell
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster set image deployment/ml-inference-xgb ml-inference=gcr.io/grad-phca/ml-inference:latest -n kafka
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster set image deployment/ml-inference-rf ml-inference=gcr.io/grad-phca/ml-inference:latest -n kafka
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster set image deployment/ml-inference-lr ml-inference=gcr.io/grad-phca/ml-inference:latest -n kafka
```

## Next Steps Based on Results

### If RPS < 1.0 (Gate Blocking)
1. Check metrics aggregator code
2. Verify Prometheus queries for RPS
3. Fix RPS calculation
4. Redeploy metrics aggregator
5. Retest

### If RPS > 1.0 but Models Predict NO_OP
1. Change constant load to 50 users (match training)
2. Or retrain models with 150-user data
3. Or remove RPS gate entirely (risky)

### If Everything Works
1. Run full proactive test
2. Run full reactive test
3. Compare results
4. Celebrate! 🎉
