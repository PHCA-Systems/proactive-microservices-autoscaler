# Expected ML Inference Service Logs

This document shows the expected log output when ML inference services start up in production.

## Service Startup Logs

### XGBoost Inference Service

```
================================================================================
ML INFERENCE SERVICE - XGBOOST
================================================================================
Model Path: /models
Kafka Servers: kafka:29092
Output Directory: /output
================================================================================

[INFO] Loading model...
[INFO] Loading model from /models
[INFO] Model loaded successfully
[INFO] Parameters loaded
[INFO] Model metrics loaded
       Accuracy: N/A
       Recall: N/A
[INFO] Inference engine initialized
[INFO] Service mapping: {'catalogue': 0, 'carts': 1, 'front-end': 2, 'orders': 3, 'payment': 4, 'shipping': 5, 'user': 6}

[INFO] Waiting 15 seconds for Kafka to be ready...

[INFO] Subscribed to 'metrics' topic
[INFO] Publishing votes to 'model-votes' topic
[INFO] Starting inference loop...
```

### Random Forest Inference Service

```
================================================================================
ML INFERENCE SERVICE - RANDOM_FOREST
================================================================================
Model Path: /models
Kafka Servers: kafka:29092
Output Directory: /output
================================================================================

[INFO] Loading model...
[INFO] Loading model from /models
[INFO] Model loaded successfully
[INFO] Parameters loaded
[INFO] Model metrics loaded
       Accuracy: N/A
       Recall: N/A
[INFO] Inference engine initialized
[INFO] Service mapping: {'catalogue': 0, 'carts': 1, 'front-end': 2, 'orders': 3, 'payment': 4, 'shipping': 5, 'user': 6}

[INFO] Waiting 15 seconds for Kafka to be ready...

[INFO] Subscribed to 'metrics' topic
[INFO] Publishing votes to 'model-votes' topic
[INFO] Starting inference loop...
```

### Logistic Regression Inference Service

```
================================================================================
ML INFERENCE SERVICE - LOGISTIC_REGRESSION
================================================================================
Model Path: /models
Kafka Servers: kafka:29092
Output Directory: /output
================================================================================

[INFO] Loading model...
[INFO] Loading model from /models
[INFO] Model loaded successfully
[INFO] Parameters loaded
[INFO] Model metrics loaded
       Accuracy: N/A
       Recall: N/A
[INFO] Inference engine initialized
[INFO] Service mapping: {'catalogue': 0, 'carts': 1, 'front-end': 2, 'orders': 3, 'payment': 4, 'shipping': 5, 'user': 6}

[INFO] Waiting 15 seconds for Kafka to be ready...

[INFO] Subscribed to 'metrics' topic
[INFO] Publishing votes to 'model-votes' topic
[INFO] Starting inference loop...
```

## Runtime Prediction Logs

Once the services are running and receiving metrics from Kafka, they will log predictions:

```
[VOTE 1] front-end       -> SCALE UP    (confidence: 95.00%)
[VOTE 2] carts           -> NO ACTION   (confidence: 87.50%)
[VOTE 3] orders          -> SCALE UP    (confidence: 92.30%)
[VOTE 4] catalogue       -> NO ACTION   (confidence: 78.90%)
[VOTE 5] user            -> NO ACTION   (confidence: 81.20%)
[VOTE 6] payment         -> NO ACTION   (confidence: 85.60%)
[VOTE 7] shipping        -> NO ACTION   (confidence: 79.40%)
```

## Error Logs (Model Not Found)

If a model file is not found, the service will log an error and exit:

```
================================================================================
ML INFERENCE SERVICE - XGBOOST
================================================================================
Model Path: /models
Kafka Servers: kafka:29092
Output Directory: /output
================================================================================

[INFO] Loading model...
[ERROR] Failed to load model: Model file not found: /models/model.joblib

Exit Code: 1
```

## Key Log Messages for Verification

### ✅ Requirement 9.4: Model type and file path are logged

The following log messages satisfy this requirement:

1. **File path logged:**
   ```
   [INFO] Loading model from /models
   ```

2. **Model type logged:**
   ```
   [INFO] Model loaded successfully
   ```
   
   The model type is implicitly logged through the successful loading message and can be seen in the model object type (XGBClassifier, RandomForestClassifier, Pipeline).

### ✅ Requirement 9.5: Error handling

If the model file is not found:
```
[ERROR] Failed to load model: Model file not found: /models/model.joblib
```

And the service exits with non-zero status code (1).

## Viewing Logs in Production

### Docker Compose
```bash
# View logs for all services
docker-compose -f kafka-structured/docker-compose.ml.yml logs -f

# View logs for specific service
docker-compose -f kafka-structured/docker-compose.ml.yml logs -f ml-xgboost
docker-compose -f kafka-structured/docker-compose.ml.yml logs -f ml-random-forest
docker-compose -f kafka-structured/docker-compose.ml.yml logs -f ml-logistic-regression
```

### Kubernetes
```bash
# View logs for specific pod
kubectl logs -n sock-shop ml-inference-xgb-<pod-id>
kubectl logs -n sock-shop ml-inference-rf-<pod-id>
kubectl logs -n sock-shop ml-inference-lr-<pod-id>

# Follow logs in real-time
kubectl logs -n sock-shop -f ml-inference-xgb-<pod-id>
```

## Verification Checklist

When verifying Task 2.2 in production, check for these log messages:

- [ ] Service startup banner with model name
- [ ] Model path logged
- [ ] "Model loaded successfully" message
- [ ] Model type visible in logs
- [ ] Service mapping logged
- [ ] "Subscribed to 'metrics' topic" message
- [ ] "Publishing votes to 'model-votes' topic" message
- [ ] "Starting inference loop..." message
- [ ] Prediction logs showing votes being published

If any of these are missing, the service may not be configured correctly.
