# Locust Failure Root Cause Analysis

## Executive Summary

**ROOT CAUSE IDENTIFIED**: GKE pods have restrictive CPU limits (100-300m) that cause slow response times when services are at 1 replica under load. This leads to Locust timeouts and high failure rates.

**Why it worked during data collection**: Docker Compose had NO resource limits - containers could use unlimited CPU/memory.

**Why it works in proactive tests**: ML models scale services to 2+ replicas during the 2-minute stabilization period, distributing load and keeping response times under 2 seconds.

---

## Detailed Analysis

### 1. Resource Limits Comparison

#### Docker Compose (Data Collection)
```yaml
# NO resource limits defined
# Containers can use unlimited CPU and memory
# Services respond quickly even at 1 replica under load
```

#### GKE (Current Testing)
```yaml
resources:
  limits:
    cpu: 100m-500m      # Very restrictive!
    memory: 100Mi-1000Mi
  requests:
    cpu: 99m-100m
    memory: 100Mi-300Mi
```

**Key Services with Tight Limits**:
- **carts**: 200m CPU limit, 200Mi memory
- **catalogue**: 100m CPU limit, 100Mi memory  
- **front-end**: 300m CPU limit, 500Mi memory
- **user**: 200m CPU limit, 200Mi memory
- **payment**: 100m CPU limit, 100Mi memory

### 2. Why Locust Fails in Reactive Tests

**Sequence of Events**:
1. Reactive test starts with all services at 1 replica
2. Load begins immediately (step pattern: 100→200→100→300→50 users)
3. Single pod with 100-300m CPU limit gets overwhelmed
4. Response times exceed 2 seconds (Locust timeout)
5. Locust marks requests as failures
6. 47-84% failure rate observed

**Evidence from Results**:
```
reactive_step_run997.jsonl:
- Interval 0: carts p95=44.2ms (violation), but mostly 0.0ms latencies
- Intervals 1-3: Mostly 0.0ms (timeouts = no response recorded)
- Interval 4-5: carts p95=36.25ms (violations)
- Interval 8-9: carts p95=471.88ms (extreme violation)
- Interval 11-12: carts p95=235.63ms (violation)

Pattern: Sporadic high latencies mixed with 0.0ms = timeouts
```

### 3. Why Proactive Tests Succeed

**Sequence of Events**:
1. Proactive test starts with all services at 1 replica
2. **2-minute stabilization period** before load starts
3. During stabilization, ML models detect baseline metrics
4. **ML models proactively scale services to 2 replicas** (front-end, carts)
5. Load begins with services already at 2+ replicas
6. Load distributed across multiple pods
7. Response times stay under 2 seconds
8. Locust success rate: ~100%

**Evidence from Results**:
```
proactive_step_run999.jsonl:
- Interval 0: front-end=2, carts=2 (ALREADY SCALED!)
- p95 latencies: 224ms, 68ms (under control)
- Only 11/20 intervals had violations (55%)
- Scaling worked: front-end 2→3→4, carts 2→3
```

### 4. Data Collection vs Current Testing

| Aspect | Data Collection (Docker) | Current Testing (GKE) |
|--------|-------------------------|---------------------|
| **CPU Limits** | None (unlimited) | 100-500m (restrictive) |
| **Memory Limits** | None (unlimited) | 100Mi-1000Mi |
| **1 Replica Performance** | Fast (no throttling) | Slow (CPU throttled) |
| **Locust Timeout** | 2 seconds | 2 seconds |
| **Failure Rate** | 0% | 47-84% (reactive) |
| **Environment** | Local Docker Compose | GKE Cloud |

### 5. Why This Matters

**The Unfair Comparison Problem**:
- Reactive tests: Services stay at 1 replica → CPU throttled → timeouts → failures
- Proactive tests: Services scale to 2+ replicas → load distributed → success

**This makes reactive look worse than it actually is** because:
1. Reactive HPA needs to observe high CPU for 5 minutes before scaling
2. During those 5 minutes, pods are throttled and Locust times out
3. Timeouts prevent accurate latency measurement
4. Can't fairly compare SLO violations when one system has 84% request failures

---

## Solutions

### Option 1: Increase GKE Resource Limits (RECOMMENDED)
**Pros**:
- Matches data collection environment
- Fair comparison between reactive and proactive
- Realistic for production (pods need headroom)

**Cons**:
- Requires redeploying all services
- May need larger GKE nodes

**Implementation**:
```yaml
# Increase CPU limits to allow burst capacity
resources:
  limits:
    cpu: 1000m      # 1 full CPU core
    memory: 1Gi
  requests:
    cpu: 100m       # Keep requests low for efficient packing
    memory: 200Mi
```

### Option 2: Increase Locust Timeout to 10s
**Pros**:
- Quick fix, no infrastructure changes
- Allows slow responses to complete

**Cons**:
- Doesn't fix the underlying CPU throttling
- 10s timeout is unrealistic for user experience
- Doesn't match data collection conditions (2s timeout)
- User explicitly rejected this solution

### Option 3: Start Reactive Tests with 2 Replicas
**Pros**:
- Quick fix, matches proactive starting state
- Fair comparison

**Cons**:
- Not realistic for reactive baseline
- Defeats the purpose of testing reactive scaling from cold start

### Option 4: Collect New Training Data on GKE
**Pros**:
- Training data matches testing environment
- Models learn GKE-specific behavior

**Cons**:
- Time-consuming (4+ hours per dataset)
- Close to graduation deadline
- Doesn't fix the fundamental resource limit issue

---

## Recommendation

**INCREASE GKE RESOURCE LIMITS** (Option 1)

**Rationale**:
1. Your training data was collected with unlimited resources
2. Your models learned to predict scaling needs based on that environment
3. GKE's restrictive limits create an artificial bottleneck
4. Production systems typically have headroom for burst capacity
5. Fair comparison requires similar resource availability

**Action Items**:
1. Update all Sock Shop deployment YAMLs with higher CPU limits (1000m)
2. Redeploy services to GKE
3. Verify services respond quickly at 1 replica under moderate load
4. Re-run validation tests (both reactive and proactive)
5. Proceed with full 34-run experiment if validation passes

**Expected Outcome**:
- Reactive tests: 0-5% Locust failure rate (similar to data collection)
- Proactive tests: Continue working as before
- Fair comparison of SLO violations and scaling behavior
- Accurate latency measurements for both conditions

---

## Next Steps

1. **Immediate**: Update deployment resource limits
2. **Validate**: Run single reactive test to confirm <5% failure rate
3. **Validate**: Run single proactive test to confirm still working
4. **Execute**: Run full 34-run experiment schedule
5. **Analyze**: Compare results with confidence in fair comparison
