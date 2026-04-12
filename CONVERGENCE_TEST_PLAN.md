# Convergence Test Plan: Proving Autoscaling Works

## Goal
Demonstrate that the autoscaling system eventually reaches a stable state with 0 (or near-0) SLO violations under sustained load.

## The Problem
Current 5-minute tests are too short to show convergence:
- System needs time to scale up
- Pods need time to start (60s)
- Cooldown periods prevent rapid scaling (5 min)
- Need to observe steady state after scaling completes

## Test Configuration

### Load Pattern
- **Pattern**: Constant
- **Users**: 150 (aggressive load)
- **Duration**: 20 minutes (4x longer than current)
- **Why 20 minutes**: 
  - 0-5 min: Initial scaling phase
  - 5-10 min: Continued scaling + pod startup
  - 10-15 min: Stabilization
  - 15-20 min: Steady state observation

### SLO Threshold Options

#### Option A: Keep 36ms (Strict Test)
- **Pros**: Tests if system can meet training-derived SLO under 3x load
- **Cons**: May never converge due to database bottlenecks
- **Expected**: High violations initially, gradual reduction, may not reach 0

#### Option B: Adjust to 50-60ms (Realistic Test)
- **Pros**: Accounts for 3x load increase, more achievable
- **Cons**: Not directly comparable to training data
- **Expected**: High violations initially, should reach near-0 after scaling

#### Option C: Empirical Derivation (RECOMMENDED)
1. Run 150-user load for 5 minutes with no autoscaling
2. Measure p95 latency at various replica counts
3. Find replica count where p95 < 36ms
4. Use that as target to verify autoscaling reaches it

### Metrics to Collect

**Every 30 seconds (40 snapshots over 20 minutes):**
1. Replica count per service
2. P95 latency per service
3. SLO violations (yes/no per service)
4. RPS per service
5. CPU/Memory per service
6. ML predictions (SCALE_UP vs NO_OP)
7. Scaling decisions made

**Success Criteria:**
- Violation rate decreases over time
- Final 5 minutes (snapshots 30-40) show < 10% violations
- Services reach stable replica count
- No oscillation (scale up/down repeatedly)

## Test Procedure

### Phase 1: Proactive Test (20 minutes)
```powershell
# 1. Configure proactive mode
kubectl delete hpa --all -n sock-shop
kubectl --context=pipeline-cluster scale deployment scaling-controller -n kafka --replicas=1

# 2. Reset cluster
kubectl scale deployment front-end carts orders catalogue user payment shipping -n sock-shop --replicas=1

# 3. Wait for stabilization
Start-Sleep -Seconds 120

# 4. Start load test (20 minutes)
ssh locust-vm "LOCUST_RUN_TIME_MINUTES=20 locust -f ~/locustfile_constant.py --headless --run-time 20m --host http://sock-shop-ip"

# 5. Collect metrics every 30s (40 snapshots)
# Run experiment collection script
```

### Phase 2: Reactive Test (20 minutes)
```powershell
# 1. Configure reactive mode
kubectl --context=pipeline-cluster scale deployment scaling-controller -n kafka --replicas=0
kubectl apply -f k8s/hpa-baseline.yaml

# 2. Reset cluster
kubectl scale deployment front-end carts orders catalogue user payment shipping -n sock-shop --replicas=1

# 3. Wait for stabilization
Start-Sleep -Seconds 120

# 4. Start load test (20 minutes)
ssh locust-vm "LOCUST_RUN_TIME_MINUTES=20 locust -f ~/locustfile_constant.py --headless --run-time 20m --host http://sock-shop-ip"

# 5. Collect metrics every 30s (40 snapshots)
```

## Expected Results

### Proactive System
**Phase 1 (0-5 min): Aggressive Scaling**
- ML models predict SCALE_UP for high-latency services
- Front-end, carts, orders scale rapidly
- Violation rate: 80-90%

**Phase 2 (5-10 min): Continued Scaling**
- Services continue scaling based on ongoing violations
- New pods start and become ready
- Violation rate: 50-70%

**Phase 3 (10-15 min): Stabilization**
- Most services reach adequate replica count
- Fewer SCALE_UP predictions
- Violation rate: 20-40%

**Phase 4 (15-20 min): Steady State**
- Services at stable replica count
- Mostly NO_OP predictions
- Violation rate: < 10% (SUCCESS)

### Reactive System (HPA)
**Phase 1 (0-5 min): Slow Scaling**
- HPA scales based on CPU (not latency)
- Slower to detect need for scaling
- Violation rate: 80-90%

**Phase 2 (5-10 min): Gradual Scaling**
- HPA continues scaling as CPU increases
- May under-scale (CPU-based, not latency-based)
- Violation rate: 60-80%

**Phase 3 (10-15 min): Partial Stabilization**
- Services reach CPU-based target
- May not address latency violations
- Violation rate: 40-60%

**Phase 4 (15-20 min): Steady State**
- Services stable at CPU-based replica count
- May still have latency violations
- Violation rate: 20-40% (WORSE than proactive)

## Analysis Plan

### Convergence Metrics
1. **Time to Convergence**: When does violation rate drop below 10%?
2. **Final Violation Rate**: Average violation rate in final 5 minutes
3. **Total Replicas Used**: Sum of all replicas across services
4. **Resource Efficiency**: Violations per replica (lower is better)

### Comparison
| Metric | Proactive | Reactive | Winner |
|--------|-----------|----------|--------|
| Time to < 10% violations | ? min | ? min | Faster is better |
| Final violation rate (15-20 min) | ?% | ?% | Lower is better |
| Total replicas at steady state | ? | ? | Lower is better (if violations equal) |
| Resource efficiency | ? | ? | Lower violations per replica is better |

### Visualization
Plot over time (40 snapshots):
1. Violation rate per service
2. Replica count per service
3. P95 latency per service
4. Aggregate violation rate

Should show:
- Proactive: Rapid decrease in violations, reaches steady state
- Reactive: Slower decrease, may not reach steady state

## Potential Issues

### Issue 1: Database Bottlenecks
**Symptom**: Violations persist even after scaling
**Cause**: Carts/orders share single database instance
**Solution**: 
- Scale databases (carts-db, orders-db to 2-3 replicas)
- Add connection pooling
- Or accept that some violations are unavoidable

### Issue 2: 36ms SLO Too Aggressive
**Symptom**: Never reaches < 10% violations
**Cause**: 36ms derived from 50-user load, not 150-user
**Solution**:
- Adjust SLO to 50-60ms for 150-user load
- Or document that 36ms is unachievable at 3x load

### Issue 3: Cooldown Prevents Convergence
**Symptom**: Scaling stops before violations eliminated
**Cause**: 5-minute cooldown blocks further scaling
**Solution**:
- Reduce cooldown to 2-3 minutes
- Or accept slower convergence

### Issue 4: Max Replicas Reached
**Symptom**: Services hit MAX_REPLICAS (10) but still violating
**Cause**: Need more replicas than allowed
**Solution**:
- Increase MAX_REPLICAS to 15-20
- Or accept that max capacity is reached

## Implementation

### Update Locust Duration
```python
# locustfile_constant.py
duration_minutes = int(os.environ.get('LOCUST_RUN_TIME_MINUTES', '20'))  # Changed from 10
```

### Update Experiment Runner
```python
# run_experiments.py
LOCUST_DURATION_MIN = 20  # Changed from 11
N_INTERVALS = 40  # Changed from 20 (20 min / 30s = 40)
```

### Update Scaling Controller Config (Optional)
```yaml
# If needed to speed up convergence
COOLDOWN_MINUTES: 3  # Reduced from 5
MAX_REPLICAS: 15  # Increased from 10
```

## Success Criteria

**Proactive System Succeeds If:**
1. Violation rate in final 5 minutes < 10%
2. Services reach stable replica count (no oscillation)
3. Converges faster than reactive system
4. Uses fewer or equal replicas than reactive

**Reactive System Comparison:**
1. May not reach < 10% violations (CPU-based, not latency-based)
2. Slower convergence
3. May use more replicas (less efficient)

## Timeline

- **Proactive test**: 20 min load + 2 min settle = 22 min
- **Reactive test**: 20 min load + 2 min settle = 22 min
- **Total**: ~45 minutes per iteration

## Deliverable

A graph showing:
- X-axis: Time (0-20 minutes)
- Y-axis: Violation rate (0-100%)
- Two lines: Proactive (blue) vs Reactive (red)
- Proactive line should drop faster and lower than reactive
- Shows proactive system achieves convergence, reactive does not

This proves your autoscaling system works!
