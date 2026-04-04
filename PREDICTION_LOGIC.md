# ML Prediction Logic

## Binary Classification

The ML models predict **binary classification** for SLA violation:

### Prediction Values
- **0** = No SLA violation predicted → **NO ACTION** (system is healthy)
- **1** = SLA violation predicted → **SCALE UP** (prevent violation)

### SLA Threshold
- **P95 Latency > 9.86ms** = SLA violated
- Models predict if this threshold will be exceeded in the next 60 seconds

## When Will You See "SCALE UP"?

Currently showing "NO ACTION" because:
- ✅ Services are idle (no load)
- ✅ Latency is very low (< 5ms)
- ✅ CPU usage is minimal
- ✅ No errors occurring

### To Trigger "SCALE UP" Predictions:

**Run a load test** to stress the services:

```cmd
cd batch
run-load-test.bat
```

This will:
1. Generate heavy traffic to Sock Shop
2. Increase latency beyond SLA threshold
3. Trigger models to predict **1** (violation)
4. Display **SCALE UP** decisions

## Example Scenarios

### Scenario 1: Idle System (Current State)
```
Metrics:
  - Request Rate: 0 RPS
  - P95 Latency: 2.5ms
  - CPU Usage: 5%
  
Prediction: 0 (NO ACTION)
Reason: All metrics healthy, no violation expected
```

### Scenario 2: Under Load
```
Metrics:
  - Request Rate: 150 RPS
  - P95 Latency: 12.5ms  ← Exceeds 9.86ms threshold!
  - CPU Usage: 75%
  
Prediction: 1 (SCALE UP)
Reason: Latency exceeds SLA, violation imminent
```

### Scenario 3: High CPU
```
Metrics:
  - Request Rate: 100 RPS
  - P95 Latency: 8.2ms
  - CPU Usage: 95%  ← Very high!
  
Prediction: 1 (SCALE UP)
Reason: High CPU indicates potential latency spike
```

## Model Voting

All 3 models vote independently:

```
Service: orders
  xgboost              -> SCALE UP   (confidence: 87%)
  random_forest        -> SCALE UP   (confidence: 82%)
  logistic_regression  -> NO ACTION  (confidence: 55%)
  
  DECISION: SCALE UP (2/3 models agree - majority voting)
```

## Load Test Patterns

### 1. Constant Load
- 50 concurrent users
- Steady traffic
- Good for baseline testing

### 2. Ramp Load
- Gradual increase from 10 to 100 users
- Simulates growing traffic
- Best for seeing gradual SCALE UP decisions

### 3. Spike Load
- Sudden burst to 200 users
- Simulates traffic spike
- Best for seeing immediate SCALE UP decisions

### 4. Step Load
- Incremental steps: 20 → 40 → 60 → 80 users
- Simulates staged growth
- Good for testing threshold detection

## Try It Now!

1. **Start the system** (if not already running):
   ```cmd
   cd batch
   start-production.bat
   ```

2. **Run a load test**:
   ```cmd
   cd batch
   run-load-test.bat
   ```
   Select option 3 (Spike load) for fastest results

3. **Watch the decisions change**:
   - Initially: All "NO ACTION"
   - Under load: Mix of "SCALE UP" and "NO ACTION"
   - Heavy load: Mostly "SCALE UP"

## Understanding the Output

```
Service: orders
------------------------------------------------------------
  xgboost              -> SCALE UP   (confidence: 87.00%)
  random_forest        -> SCALE UP   (confidence: 82.00%)
  logistic_regression  -> NO ACTION  (confidence: 55.00%)
------------------------------------------------------------
  DECISION: SCALE UP
  Vote Count: 2 SCALE UP, 1 NO ACTION (3 total)
  Average Confidence: 74.67%
```

**Interpretation**:
- 2 out of 3 models predict SLA violation
- Majority voting → SCALE UP decision
- High confidence (74.67%) in the decision
- Action: Increase replicas for "orders" service

## Note

There is **no "SCALE DOWN"** decision. The system only predicts:
- **SCALE UP**: When violation is imminent
- **NO ACTION**: When system is healthy

Scaling down would be handled by a separate policy based on sustained low utilization.
