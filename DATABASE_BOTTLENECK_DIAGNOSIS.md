# Database Bottleneck Diagnosis - Your Cluster

## Current State

### Database Replicas
| Database | Replicas | CPU | Memory |
|----------|----------|-----|--------|
| carts-db | 2 | 6m each | 87-100Mi |
| orders-db | 1 | 6m | 76Mi |
| catalogue-db | 1 | 2m | 238Mi |
| user-db | 1 | 9m | 38Mi |
| session-db | 1 | 4m | 6Mi |

### Service Replicas (After Test)
| Service | Replicas | CPU | Memory |
|---------|----------|-----|--------|
| carts | 3 | 3-7m each | 400-572Mi |
| orders | 2 | 3-5m each | 301-310Mi |
| catalogue | 2 | 1-2m each | 7-10Mi |
| user | 2 | 2m each | 8-12Mi |

## Analysis

### Good News: Databases Are NOT Heavily Loaded
- All database CPU < 10m (very low)
- Database memory usage is reasonable
- No obvious resource exhaustion

### The Real Issue: Single Database Instances

**orders-db (1 replica)**
- Handles writes from 2 orders service pods
- During test: 104 checkout errors (500 Internal Server Error)
- This is the smoking gun! ← DATABASE BOTTLENECK

**carts-db (2 replicas)**
- Already scaled to 2 (good!)
- But still had 164 add_to_cart errors + 37 clear_cart errors
- May need 3 replicas for 150-user load

**catalogue-db, user-db (1 replica each)**
- Low CPU, no errors reported
- Probably not bottlenecks

## The Errors Tell the Story

From your test:
```
164 × POST add_to_cart (500 Internal Server Error)     ← carts-db bottleneck
104 × POST checkout (500 Internal Server Error)        ← orders-db bottleneck
55 × POST add_for_checkout (500 Internal Server Error) ← orders-db bottleneck
37 × DELETE clear_cart (500 Internal Server Error)     ← carts-db bottleneck
```

**All errors are database operations!**

## Why Low CPU But Still Errors?

Database bottlenecks aren't always about CPU. They can be:

1. **Connection Pool Exhaustion**
   - Database has limited connections (e.g., 100)
   - 3 carts pods × 50 connections each = 150 connections needed
   - Database rejects new connections → 500 error

2. **Lock Contention**
   - Multiple pods try to write to same row
   - Database locks the row
   - Other pods wait → timeout → 500 error

3. **Transaction Conflicts**
   - MongoDB/MySQL transaction isolation
   - Concurrent writes conflict
   - Some transactions fail → 500 error

4. **Disk I/O Limits**
   - Database writes to disk
   - Disk has limited IOPS
   - Writes queue up → slow → timeout → 500 error

**CPU is low because pods are WAITING, not computing!**

## Should You Have Scaled Databases?

### For Your Research: YES

**Why:**
1. You're testing SERVICE autoscaling, not database scaling
2. Databases should not be the bottleneck
3. Pre-scaling databases isolates the variable you're testing

**Analogy:**
- Testing car engine performance
- Don't want to run out of gas during test
- Fill the tank first (pre-scale databases)
- Then test the engine (service autoscaling)

### For Production: MAYBE

In production, you'd:
1. Use managed databases (Cloud SQL, MongoDB Atlas)
2. They auto-scale based on load
3. Or use connection pooling, read replicas, caching

But for your research, you want to isolate service autoscaling.

## Recommendation: Pre-scale Databases

### Test Plan

**Experiment 1: Current State (Baseline)**
- Keep databases as-is (orders-db: 1, carts-db: 2)
- Run 20-minute test
- Measure violations and errors
- **Hypothesis**: High errors, violations don't converge

**Experiment 2: Scaled Databases**
- Scale orders-db to 3 replicas
- Scale carts-db to 3 replicas
- Run 20-minute test
- Measure violations and errors
- **Hypothesis**: Fewer errors, violations converge to < 10%

**Comparison**:
| Metric | Baseline | Scaled DBs | Improvement |
|--------|----------|------------|-------------|
| Error rate | ?% | ?% | Should decrease |
| Final violations | ?% | ?% | Should decrease |
| Time to convergence | ? min | ? min | Should be faster |

### Implementation

```powershell
# Scale databases
kubectl scale deployment orders-db -n sock-shop --replicas=3
kubectl scale deployment carts-db -n sock-shop --replicas=3

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=orders-db -n sock-shop --timeout=120s
kubectl wait --for=condition=ready pod -l app=carts-db -n sock-shop --timeout=120s

# Verify
kubectl get deployments -n sock-shop | Select-String "db"
```

## What About catalogue-db and user-db?

**Don't scale them (yet)**:
- No errors reported for catalogue or user operations
- Low CPU usage
- Not the bottleneck

If you still see violations after scaling orders-db and carts-db, THEN consider scaling the others.

## Should Databases Be in Your ML Model?

### NO - Here's Why:

**1. Different Problem Domain**
- Your research: Service autoscaling based on application metrics
- Database scaling: Different metrics, different strategies

**2. Complexity**
- Database scaling requires replication setup
- Master-slave configuration
- Data consistency concerns
- Out of scope for your thesis

**3. Training Data**
- Your models trained on service metrics (RPS, latency, CPU)
- No database metrics in training data
- Can't predict database bottlenecks

**4. Academic Focus**
- Your contribution: ML-driven service autoscaling
- Database scaling: Separate research problem
- Keep scope focused

### What You SHOULD Do:

**For Your Thesis:**
1. Pre-scale databases to eliminate bottleneck
2. Focus on service autoscaling effectiveness
3. Document: "Databases pre-scaled to isolate service autoscaling"

**In Your Paper:**
```
To isolate the effects of service-level autoscaling, database 
instances were pre-scaled to 3 replicas to ensure they did not 
become bottlenecks. This allows us to evaluate the effectiveness 
of ML-driven service autoscaling without confounding factors from 
database resource constraints.
```

## Next Steps

1. **Scale databases** (orders-db, carts-db to 3 replicas)
2. **Run 20-minute convergence test** (proactive)
3. **Measure**:
   - Error rate (should drop significantly)
   - Violation rate over time (should converge to < 10%)
   - Time to convergence (should be faster)
4. **Compare to baseline** (if you want)
5. **Run reactive test** with scaled databases
6. **Compare proactive vs reactive** (fair comparison)

This will show whether databases were the bottleneck all along!
