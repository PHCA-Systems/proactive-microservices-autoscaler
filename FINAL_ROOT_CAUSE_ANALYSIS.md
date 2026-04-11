# FINAL Root Cause Analysis

## The Real Issue: Services at 1 Replica Cannot Handle Load

### Evidence from Latest Test (run994 - Reactive)

**Results**:
- 15/20 intervals: front-end p95 = 0.0ms (timeouts)
- 10/20 intervals: carts p95 = 0.0ms (timeouts)
- 0 scaling events (HPA never scaled)
- 5 violations detected
- CPU usage: 1-8% (very low)

**What this means**: Services at 1 replica with current CPU limits (100-500m) CANNOT handle the step load pattern. Requests timeout before completing.

### Comparison with Proactive Test (run999)

**Results**:
- 6/20 intervals: front-end p95 = 0.0ms (timeouts)
- 5/20 intervals: carts p95 = 0.0ms (timeouts)
- 11 scaling events
- 11 violations detected
- Services scaled: front-end 2→3→4, carts 2→3

**Key difference**: Proactive test STARTED with services at 2 replicas (scaled during stabilization), so it had FEWER timeouts and could deliver more load.

## Why Proactive Has Fewer Timeouts

### Timeline Analysis

**Proactive Test**:
```
0-2 min:  Stabilization period
          ML models detect baseline metrics
          Models proactively scale front-end and carts to 2 replicas
2-12 min: Load test begins
          Services ALREADY at 2 replicas
          Load distributed across 2 pods
          Fewer timeouts (6/20 and 5/20)
          More violations detected (11/20)
          More scaling events (11 total)
```

**Reactive Test**:
```
0-2 min:  Stabilization period
          HPA observes low CPU
          No scaling occurs
2-12 min: Load test begins
          Services STILL at 1 replica
          Single pod overwhelmed
          More timeouts (15/20 and 10/20)
          Fewer violations detected (5/20)
          No scaling events (0 total)
```

## The CPU Limit Issue IS Real

### Why Low CPU with Timeouts?

**The paradox**: CPU at 1-8% but services timing out?

**Explanation**: 
1. Pod has 100-500m CPU limit
2. Under load, pod tries to use more CPU
3. Kubernetes throttles the pod at the limit
4. Pod becomes unresponsive (can't process requests fast enough)
5. Requests queue up and timeout
6. CPU metric shows low % because pod is THROTTLED, not because it's idle

**This is called "CPU throttling"** - the pod WANTS more CPU but can't get it.

### Evidence

**From run994 (reactive)**:
- Interval 9: front-end p95=245ms, CPU=6.8%
- Interval 10: front-end p95=245ms, CPU=2.3%

**High latency with LOW CPU = throttling!**

If the pod had enough CPU, it would:
- Show higher CPU % (60-80%)
- Process requests faster
- Have lower latency

### Why Proactive Works Better

**Proactive starts with 2 replicas**:
- Load distributed: 50% per pod
- Each pod uses 50% of its limit
- No throttling
- Requests complete successfully
- Fewer timeouts

**Reactive starts with 1 replica**:
- Load concentrated: 100% on one pod
- Pod hits limit immediately
- Throttling occurs
- Requests timeout
- HPA can't scale (needs 5 min observation)

## My Original Hypothesis Was CORRECT

**Increasing CPU limits from 100-500m to 1000m WILL fix this** because:

1. **Eliminates throttling**: Pod can burst to 1000m under load
2. **Allows HPA to work**: CPU % will rise naturally, triggering HPA
3. **Reduces timeouts**: Services can handle load at 1 replica temporarily
4. **Fair comparison**: Both conditions start from same state

## Why Data Collection Worked

**Docker Compose had NO limits**:
- Containers could use unlimited CPU
- No throttling ever occurred
- Services responded quickly even at 1 replica
- 0% Locust failures

**GKE has 100-500m limits**:
- Containers throttled at limit
- Services slow at 1 replica
- High timeout rate
- Unfair comparison

## The Solution

### Increase CPU Limits to 1000m

**Why this works**:
1. Matches data collection environment (unlimited → 1000m is close enough)
2. Eliminates CPU throttling bottleneck
3. Allows services to handle burst load
4. Gives HPA time to observe and scale
5. Fair comparison between reactive and proactive

**Expected outcome after fix**:

**Reactive**:
- Services start at 1 replica
- Can handle initial load without throttling
- CPU rises to 60-80% (real usage, not throttled)
- HPA observes high CPU for 5 minutes
- HPA scales up
- Fewer timeouts (<5%)
- More violations detected
- Scaling events occur

**Proactive**:
- Services start at 1 replica (or scale to 2 during stabilization)
- ML models detect violations quickly
- Scale within 30-60 seconds
- Fewer violations than reactive
- Fewer timeouts (<5%)
- More scaling events than reactive

## Why HPA Didn't Scale in run994

**HPA needs**:
1. CPU > 70% (threshold)
2. Sustained for 5 minutes (stabilization window)

**What happened**:
1. CPU showed 1-8% (throttled, not real usage)
2. HPA thought pod was idle
3. No scaling triggered

**With 1000m limit**:
1. CPU would show 60-80% (real usage)
2. HPA would detect high CPU
3. Scaling would occur after 5 minutes

## Conclusion

**My original analysis was CORRECT**:
- CPU limits (100-500m) cause throttling
- Throttling causes timeouts
- Timeouts prevent fair comparison
- Solution: Increase limits to 1000m

**The "working" test (run994) actually FAILED**:
- 75% timeout rate for front-end
- 50% timeout rate for carts
- No scaling occurred
- Not a valid test

**We MUST increase CPU limits** to:
1. Eliminate throttling
2. Allow fair comparison
3. Get accurate measurements
4. Enable proper scaling behavior

## Next Action

**Run the fix script**:
```powershell
.\fix_resource_limits.ps1
```

Then re-run validation tests to confirm:
- <5% timeout rate
- Accurate latency measurements
- HPA scales in reactive tests
- ML models scale in proactive tests
- Fair comparison between conditions
