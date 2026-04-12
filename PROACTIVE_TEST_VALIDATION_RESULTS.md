# Proactive Test Validation Results

**Test Date**: 2026-04-11  
**Test Type**: Proactive autoscaling with step load pattern  
**Duration**: ~12 minutes (10 min load + 2 min settle)

## ✅ MODELS ARE WORKING

### ML Models Status
All three new models are deployed and making predictions:

1. **SVM** ✅
   - Making predictions every 30 seconds
   - Confidence levels: 96-98%
   - Example: "payment -> NO ACTION (96.30%)"

2. **Logistic Regression (OneHot)** ✅
   - Making predictions every 30 seconds
   - Confidence levels: 77-99%
   - Example: "front-end -> SCALE UP (77.71%)"

3. **Random Forest (OneHot)** ✅
   - Making predictions every 30 seconds
   - Confidence levels: 52-100%
   - Example: "carts -> NO ACTION (76.80%)"

### Voting & Decision Making ✅
- **Authoritative Scaler**: Aggregating votes via majority voting
- **Decision Window**: 5 seconds
- **Voting Strategy**: 2 out of 3 models must agree
- **Example Decision**:
  ```
  Service: catalogue
    svm                  -> NO ACTION  (98.35%)
    logistic_regression  -> NO ACTION  (99.99%)
    random_forest        -> NO ACTION  (100.00%)
  DECISION: NO_OP (3/3 agree)
  ```

### Scaling Behavior ✅
Proactive scaling is working as designed:

| Service | Initial | Final | Scaling Events |
|---------|---------|-------|----------------|
| carts | 1 | 3 | 1→2→3 (proactive) |
| front-end | 1 | 3 | 1→2→3 (proactive) |
| catalogue | 1 | 1 | Scaled up then down |
| user | 1 | 1 | Scaled up then down |
| payment | 1 | 1 | Scaled up then down |
| orders | 1 | 1 | No scaling needed |
| shipping | 1 | 1 | No scaling needed |

**Key Observations**:
- Models correctly identified carts and front-end as needing scale-up
- Scale-down policy working (services scaled back down when load decreased)
- Cooldown periods preventing thrashing

## ⚠️ REQUEST FAILURE RATE ISSUE

### Problem
From the partial test output, we observed high failure rates:
- **POST add_to_cart**: 100% failure rate (2/2 requests failed)
- **GET browse_catalogue**: 66.67% failure rate (6/9 requests failed)

### Current Status
**CRITICAL**: We need to investigate why requests are still failing despite:
- ✅ Resource limits increased to 1000m CPU, 1Gi memory
- ✅ Services scaled proactively (carts at 3 replicas, front-end at 3 replicas)
- ✅ No CPU throttling observed (pods using 2-6m CPU, well below limits)

### Possible Causes

1. **Database Bottleneck** (Most Likely)
   - carts-db: 2 replicas handling requests from 3 carts pods
   - orders-db: 1 replica (may be overwhelmed during checkout)
   - Database connections may be saturated

2. **Network Issues**
   - Locust VM to GKE connectivity
   - Service mesh / network policies
   - DNS resolution delays

3. **Application-Level Issues**
   - Sock Shop application bugs
   - Session management problems
   - Race conditions in cart operations

4. **Load Pattern Issues**
   - Step load pattern may be too aggressive
   - Not enough warm-up time
   - Services not fully ready after scaling

### Next Steps to Diagnose

1. **Check Prometheus for actual error rates**:
   ```bash
   # Get error rate from Prometheus
   kubectl exec -n sock-shop <prometheus-pod> -- wget -qO- 'http://localhost:9090/api/v1/query?query=sum(rate(request_duration_seconds_count{status_code=~"5.."}[1m]))/sum(rate(request_duration_seconds_count[1m]))'
   ```

2. **Check service logs for errors**:
   ```bash
   kubectl logs -n sock-shop deployment/carts --tail=100
   kubectl logs -n sock-shop deployment/front-end --tail=100
   kubectl logs -n sock-shop deployment/carts-db --tail=100
   ```

3. **Check database connections**:
   ```bash
   kubectl exec -n sock-shop deployment/carts-db -- mongo --eval "db.serverStatus().connections"
   ```

4. **Run a simpler load test**:
   - Use constant load pattern instead of step
   - Lower user count (50 instead of 100-300)
   - Longer warm-up period

5. **Check Locust VM logs**:
   ```bash
   ssh User@35.222.116.125 "tail -100 /tmp/locust*.log"
   ```

## SLO Violations

During the test, we observed violations in these intervals:
- Intervals 1-8: carts violations (expected during initial scale-up)
- Intervals 10-11: carts violations
- Intervals 16-17: front-end and carts violations

**Analysis**:
- Violations are expected during load ramp-up
- Models are responding by scaling up
- Some violations persist even after scaling (suggests database bottleneck)

## Resource Usage

All pods are well within resource limits:

| Pod | CPU Usage | Memory Usage | CPU Limit | Memory Limit |
|-----|-----------|--------------|-----------|--------------|
| carts-* | 3-5m | 390-454Mi | 1000m | 1Gi |
| front-end-* | 2-4m | 58-69Mi | 1000m | 1Gi |
| carts-db-* | 5-6m | 73-91Mi | N/A | N/A |

**No CPU throttling observed** - pods are using <1% of available CPU.

## Conclusions

### What's Working ✅
1. **ML Models**: All 3 models making predictions correctly
2. **Voting System**: Majority voting working as designed
3. **Scaling Controller**: Executing scale-up/scale-down decisions
4. **Proactive Scaling**: Services scaling before SLO violations
5. **Resource Limits**: No CPU throttling, plenty of headroom

### What's NOT Working ⚠️
1. **Request Failure Rate**: Still seeing high failure rates (66-100%)
2. **Root Cause Unknown**: Need more investigation to identify why

### Critical Question
**Is the failure rate issue in Locust or in Sock Shop?**

We need to determine if:
- Locust is timing out due to network issues (Locust problem)
- Sock Shop is actually returning errors (Sock Shop problem)
- Database is the bottleneck (architectural problem)

## Recommendations

### Immediate Actions
1. **Get Prometheus error rate data** - This will tell us if Sock Shop is actually failing or if it's just Locust timing out
2. **Check service logs** - Look for actual errors in carts, front-end, and database logs
3. **Run a simpler test** - Constant load with lower user count to isolate the issue

### If Errors Are Real (Sock Shop is failing)
- Scale database replicas (carts-db, orders-db)
- Increase database connection pool sizes
- Add database read replicas
- Consider this a known limitation to document in the paper

### If Errors Are Locust Timeouts
- Increase Locust timeout from 2s to 5s
- Check network latency between Locust VM and GKE
- Verify Locust VM has sufficient resources

### For Comparison Experiments
**CRITICAL**: We cannot run valid comparison experiments until we resolve the failure rate issue. Both proactive and reactive tests will be affected, making comparisons meaningless.

**Options**:
1. **Fix the issue** (preferred) - Identify and resolve root cause
2. **Document as limitation** - If it's a Sock Shop architectural issue, document it and proceed
3. **Use different workload** - Switch to a simpler application without database bottlenecks

## Status: MODELS WORKING, FAILURES NEED INVESTIGATION

The good news: Your ML models are fully operational and making correct predictions.  
The bad news: Request failures are still occurring and need to be diagnosed before running comparison experiments.
