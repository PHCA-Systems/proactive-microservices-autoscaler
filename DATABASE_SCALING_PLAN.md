# Database Scaling Plan

## Problem
Scaling carts and orders services has minimal effect on p95 latency because their databases (carts-db, orders-db) are bottlenecked at 1-2 replicas.

**Evidence:**
- Orders: Scaling 1→5 replicas INCREASED p95 by 105% (58.7ms → 120.8ms avg)
- Carts: Scaling 1→5 replicas only reduced p95 by 16% (61.3ms → 51.5ms avg)
- Front-end: Scaling 2→5 replicas reduced p95 by 17% (proper behavior)

## Solution Options

### Option 1: Add Databases to Proactive Autoscaling (RECOMMENDED)
Treat databases as scalable services in the ML-based autoscaling system.

**Steps:**
1. Add carts-db and orders-db to MONITORED_SERVICES in run_config.py
2. Collect training data for databases (RPS, CPU, memory, p95 latency)
3. Train ML models to predict when databases need scaling
4. Update scaling-controller to scale database deployments
5. Re-run experiments with database scaling enabled

**Pros:**
- Consistent with your ML-based approach
- Databases scale proactively based on predicted load
- Shows your system handles stateful services

**Cons:**
- Requires retraining models with database features
- Databases are stateful (scaling down loses data unless using persistent volumes)
- More complex

**Timeline:** 2-3 hours (add to monitoring, retrain, test)

---

### Option 2: Static Database Scaling (QUICK FIX)
Manually scale databases to sufficient replicas before experiments.

**Steps:**
1. Scale orders-db to 3 replicas: `kubectl scale deployment orders-db -n sock-shop --replicas=3`
2. Scale carts-db to 3 replicas: `kubectl scale deployment carts-db -n sock-shop --replicas=3`
3. Re-run convergence tests
4. Compare results with/without database scaling

**Pros:**
- Immediate fix (5 minutes)
- Proves database was the bottleneck
- No code changes needed

**Cons:**
- Not "autoscaling" - just pre-scaled
- Doesn't show your system adapting to database load
- Uses more resources than needed

**Timeline:** 5 minutes

---

### Option 3: Hybrid Approach (BEST FOR PAPER)
Use static database scaling for experiments, document as limitation/future work.

**Steps:**
1. Scale databases statically to 3 replicas
2. Re-run all experiments with scaled databases
3. In paper, document:
   - "Database tier was pre-scaled to eliminate bottleneck"
   - "Future work: Extend autoscaling to stateful database tier"
   - Show comparison: with/without database scaling

**Pros:**
- Quick to implement
- Focuses paper on application-tier autoscaling
- Honest about limitations
- Shows you understand the problem

**Cons:**
- Doesn't fully solve the problem
- Reviewers might ask "why not scale databases?"

**Timeline:** 10 minutes + re-run experiments

---

## Recommended Approach: Option 3 (Hybrid)

**Rationale:**
- You're close to graduation - need results fast
- Database autoscaling is complex (stateful, data persistence)
- Most autoscaling research focuses on stateless application tier
- Documenting limitation shows maturity

**Implementation:**

```bash
# 1. Scale databases
kubectl scale deployment orders-db -n sock-shop --replicas=3
kubectl scale deployment carts-db -n sock-shop --replicas=3

# 2. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l name=orders-db -n sock-shop --timeout=120s
kubectl wait --for=condition=ready pod -l name=carts-db -n sock-shop --timeout=120s

# 3. Fix experiment timing (21 minutes for 40 snapshots)
# Already done in run_experiments.py

# 4. Re-run convergence tests
cd kafka-structured/experiments
python run_experiments.py
```

**Expected Results:**
- Carts and orders p95 latency should drop below 36ms threshold
- Both proactive and reactive should achieve <10% violations
- Proactive should converge faster than reactive

**Paper Section:**
```
5.3 Database Tier Considerations

Our evaluation revealed that application-tier autoscaling alone is 
insufficient when the database tier becomes the bottleneck. Scaling 
the orders service from 1 to 5 replicas increased average p95 latency 
by 105% because all replicas contended for a single database instance.

To isolate the effectiveness of application-tier autoscaling, we 
pre-scaled database deployments (orders-db and carts-db) to 3 replicas. 
This eliminated the database bottleneck and allowed us to evaluate 
the autoscaling system's ability to adapt application-tier resources 
to workload demands.

Future work could extend our ML-based approach to the database tier, 
though this introduces challenges related to state management and 
data consistency during scale operations.
```

---

## Alternative: If You Want Full Database Autoscaling

**Steps:**
1. Add databases to monitored services
2. Modify metrics-aggregator to collect database metrics
3. Update ML models to include database features
4. Modify scaling-controller to handle database scaling
5. Add logic to prevent scale-down when database has active connections

**Timeline:** 4-6 hours

**Risk:** High - databases are stateful, scaling is complex

---

## Decision Point

**What do you want to do?**

A. **Quick fix (Option 2):** Scale databases now, re-run tests (5 min)
B. **Hybrid (Option 3):** Scale databases, document limitation (10 min)
C. **Full solution (Option 1):** Add databases to autoscaling system (3 hours)

I recommend **Option 3** given your timeline.
