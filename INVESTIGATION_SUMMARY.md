# Investigation Summary: Why Both Tests Show 90% Violations

## What We Know For Sure

### 1. Both Tests Showed Similar Behavior
- Proactive run6000: 90% violations (18/20 intervals)
- Reactive run6001: 90% violations (18/20 intervals)
- Both scaled services, but inadequately

### 2. Scaling Controller Timeline
- Scaled UP at 02:53 UTC (2 min before proactive test)
- Scaled DOWN at 03:11 UTC (4 min after proactive test)
- **The scaling-controller WAS running during the proactive test**

### 3. ML Models Voting Pattern
- All 3 models (RF, LR, SVM) voting NO_ACTION with 100% confidence
- Last SCALE_UP decision: 01:31 UTC (1.5 hours before proactive test)
- During proactive test: All decisions were NO_OP

### 4. HPA Status
- HPAs created at 01:11 UTC
- HPAs were active during BOTH tests
- Kubernetes events show HPA scaled services during reactive test

### 5. The RPS Gate
```python
RPS_THRESHOLD = 1.0  # Minimum RPS to consider scaling

if rps < RPS_THRESHOLD:
    return 0, 1.0, 1.0  # NO_OP with 100% confidence
```

## The Critical Questions

### Q1: Were HPAs active during the proactive test?
**Evidence suggests YES**:
- HPAs exist and were created before the test
- The experiment runner's `enable_proactive()` should delete them, but they're still there
- If HPAs weren't deleted, they would have been active

**But**: We don't have direct evidence of HPA scaling during proactive test (events expired)

### Q2: Why are models voting NO_ACTION with 100% confidence?
**Two possibilities**:

**A) RPS Gate is Blocking**:
- If RPS < 1.0, models return NO_OP with 100% confidence
- But during 150-user load test, RPS should be much higher than 1.0
- Front-end should have RPS of 50-150 (depending on request rate)

**B) Models Genuinely Predict No Violation**:
- Models trained on 50-user load
- Testing with 150-user load (3x higher)
- Feature distributions are completely different
- Models might be confused and predicting NO_OP

### Q3: Did the experiment runner work correctly?
**Unknown**:
- We don't know if you ran `run_experiments.py` or manually started tests
- The `enable_proactive()` function should:
  1. Delete all HPAs
  2. Scale scaling-controller to 1 replica
- But HPAs still exist, suggesting it didn't work

## Most Likely Scenario

### Scenario A: Proactive System Wasn't Actually Proactive
1. Experiment runner's `enable_proactive()` failed to delete HPAs
2. HPAs remained active during "proactive" test
3. Scaling-controller was running but making NO_OP decisions
4. HPA did all the scaling in both tests
5. Both tests were effectively reactive

**Evidence FOR**:
- HPAs still exist
- All models voting NO_ACTION
- Similar scaling behavior in both tests

**Evidence AGAINST**:
- Scaling-controller was definitely running during proactive test
- We saw different scaling patterns (proactive scaled more services)

### Scenario B: RPS Gate is Blocking Everything
1. Metrics aggregator is publishing RPS < 1.0 for all services
2. RPS gate blocks all predictions
3. Models return NO_OP with 100% confidence
4. Scaling-controller has nothing to execute
5. HPA does all the scaling

**Evidence FOR**:
- All models voting NO_ACTION with 100% confidence
- This is exactly what RPS gate would produce

**Evidence AGAINST**:
- During 150-user load test, RPS should be much higher than 1.0
- Doesn't make sense that RPS would be < 1.0 under load

### Scenario C: Models Are Broken for 150-User Load
1. Models trained on 50-user load
2. Testing with 150-user load (3x higher)
3. Feature distributions are out of training range
4. Models predict NO_OP because they're confused
5. HPA does all the scaling

**Evidence FOR**:
- Training/testing mismatch (50 vs 150 users)
- Models might not generalize to 3x load

**Evidence AGAINST**:
- Models should still see high latency and predict SCALE_UP
- 100% confidence on NO_OP is suspicious (suggests RPS gate, not confusion)

## What We Need To Do

### Immediate Actions

1. **Check if RPS gate is the issue**:
   - Add logging to inference.py to print RPS values
   - Rebuild and redeploy ML inference services
   - Run a short test and check logs

2. **Verify HPA behavior**:
   - Manually delete all HPAs
   - Verify they're gone
   - Run a short proactive test
   - Check if services scale

3. **Test the experiment runner**:
   - Run `enable_proactive()` function manually
   - Verify it deletes HPAs
   - Verify it scales scaling-controller to 1
   - Fix any errors

### Root Cause Determination

**If RPS < 1.0 in logs**:
- Metrics aggregator is broken
- Fix the RPS calculation
- Redeploy and retest

**If RPS > 1.0 but models still vote NO_ACTION**:
- Models are broken for 150-user load
- Either:
  - Test with 50 users (matching training)
  - Retrain models with 150-user data

**If HPAs can't be deleted**:
- Fix the experiment runner
- Ensure proper RBAC permissions
- Manually delete HPAs before each test

## Recommendation

**Start with #1**: Add logging to see RPS values. This is the quickest way to determine if the RPS gate is the culprit.

If RPS is fine, then we know the issue is either:
- Models not generalizing to 150-user load
- HPAs interfering with proactive system

We can tackle those next.
