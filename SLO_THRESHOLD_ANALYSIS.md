# SLO Threshold Analysis: Training vs Testing Discrepancy

## Problem Statement

The 36ms SLO threshold was calculated from training data showing ~12% violation rate, but current experiments with the same threshold produce 90% violations. This analysis investigates what changed.

## Root Cause: USER COUNT MISMATCH

### Training Data Collection (Historical)
- **Load Pattern**: Constant
- **User Count**: 50 users
- **Duration**: 10 minutes per run
- **Runs**: 4 constant runs (run_1 through run_4)
- **SLO Calculation**: P75 of front-end p95 latency = 35.68ms
- **Expected Violation Rate**: ~12% (24.6% for constant pattern specifically)

**Evidence from SESSION_SUMMARY.md:**
```
Run the system at comfortable load (constant pattern, 50 users).
Observe the p95 latency the front-end naturally produces under these conditions.
```

**Evidence from apply_sla_labels.py:**
```python
# SLA threshold: 35.68ms (P75 of front-end p95 under constant load, 50 users)
```

**Evidence from ML-Models/README.md:**
```
1. Run system at comfortable load (constant pattern, 50 users)
2. Observe p95 latency of front-end service
3. Take P75 of observations as SLA threshold
```

### Current Testing (Now)
- **Load Pattern**: Constant
- **User Count**: 150 users (3x higher!)
- **Duration**: 11 minutes
- **Runs**: run6000 (proactive), run6001 (reactive)
- **SLO Threshold**: 36ms (same as training)
- **Actual Violation Rate**: 90% (18/20 intervals)

**Evidence from locustfile_constant.py (current):**
```python
self.user_count = 150  # Target constant user count (peak load)
```

**Evidence from proactive_constant_run6000.jsonl:**
- Interval 0: front-end p95 = 67.5ms (87% over threshold)
- Interval 1: front-end p95 = 51.9ms (44% over threshold)
- Interval 2: front-end p95 = 67.6ms (88% over threshold)
- Interval 3: front-end p95 = 54.8ms (52% over threshold)
- Interval 4: front-end p95 = 45.9ms (28% over threshold)

## Why This Happened

### Timeline of Changes

1. **Original Training Data Collection**: Used 50 users for constant pattern
   - File: `load_shapes.py` and `locustfile.py` both had `user_count = 50`
   - This was the "comfortable load" used to derive the 35.68ms threshold

2. **Recent Change**: Modified constant pattern to 150 users
   - File: `locustfile_constant.py` changed to `user_count = 150`
   - Comment says "peak load" instead of "comfortable load"
   - This change was made to test system under higher stress

3. **Result**: Testing with 3x the load used during training
   - 50 users → 35.68ms p95 latency (comfortable, 24.6% violations)
   - 150 users → 50-70ms p95 latency (stressed, 90% violations)

## Validation

### Training Data Violation Rates (from SESSION_SUMMARY.md)
| Pattern  | % Rows Exceeding 35.68ms Threshold |
|----------|-------------------------------------|
| constant | 24.6%                               |
| ramp     | 81.8%                               |
| spike    | 54.5%                               |
| step     | 88.6%                               |

The constant pattern at 50 users produced 24.6% violations - this is the "comfortable load" baseline.

### Current Test Results (150 users)
| Run      | Violations | Rate  | User Count |
|----------|------------|-------|------------|
| run6000  | 18/20      | 90%   | 150        |
| run6001  | 18/20      | 90%   | 150        |

The 90% violation rate with 150 users is comparable to the step pattern (88.6%) from training data, which used 50-300 users with sudden jumps.

## Academic Integrity Implications

### The Issue
You are correct that changing the SLO threshold between training and testing would be academically dishonest. However, the threshold itself hasn't changed - the load pattern has.

### What Actually Happened
- Training: "comfortable load" = 50 users → 35.68ms threshold → 12% violations
- Testing: "peak load" = 150 users → 35.68ms threshold → 90% violations

### The Mismatch
The 35.68ms threshold is valid for 50-user constant load. It is NOT valid for 150-user constant load. The threshold represents "P75 of p95 latency under comfortable load" - but 150 users is not comfortable load, it's peak load.

## Solutions

### Option 1: Match Training Conditions (RECOMMENDED)
**Change constant load back to 50 users for fair comparison**

Pros:
- Academically sound - testing matches training conditions
- SLO threshold remains valid
- Expected violation rate: ~12-25%
- Fair comparison between proactive and reactive

Cons:
- Lower stress test
- May not reveal scaling behavior under peak load

### Option 2: Recalculate SLO for 150 Users
**Run new training data collection with 150 users, derive new threshold**

Pros:
- Tests system under peak load
- New threshold would be valid for 150 users

Cons:
- Requires complete retraining of all ML models
- Invalidates all existing training data
- Time-consuming (you're close to graduation)
- Changes the research methodology mid-stream

### Option 3: Use Mixed Load Patterns
**Run step/ramp/spike patterns which were trained with variable load**

Pros:
- These patterns include 150-user load in training data
- SLO threshold is valid for these patterns
- More realistic workload variation

Cons:
- Harder to compare proactive vs reactive (cooldown periods)
- More complex analysis

## Recommendation

**Use Option 1: Change constant load back to 50 users**

This is the academically sound approach because:
1. It matches the training conditions exactly
2. The SLO threshold remains valid
3. You can fairly compare proactive vs reactive
4. No retraining required
5. Consistent with your research methodology

The 150-user constant load is essentially a different experiment - it's testing the system under conditions it wasn't trained for. The high violation rate (90%) is expected and correct, but it doesn't allow for meaningful comparison because both systems are overwhelmed.

## Action Items

1. Change `locustfile_constant.py` back to `user_count = 50`
2. Re-run constant load tests for both proactive and reactive
3. Expected results: ~12-25% violation rate, meaningful difference between conditions
4. Document this finding in your thesis as a lesson about matching test conditions to training conditions

## Key Takeaway

The SLO threshold is environment-specific AND load-specific. The 35.68ms threshold is valid for:
- GKE environment (not local Docker)
- 50-user constant load (not 150-user)
- Front-end p95 latency metric

Testing with 150 users requires either:
- A new SLO threshold derived from 150-user training data, OR
- Accepting that you're testing outside the trained operating range
