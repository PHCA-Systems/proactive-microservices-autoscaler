# Database Bottleneck Analysis

## What is a Database Bottleneck?

When you scale a service (e.g., carts from 1 → 3 replicas), you get:
- 3 pods handling requests
- 3x the request processing capacity

BUT all 3 pods connect to the SAME database instance:
```
carts-pod-1 ──┐
carts-pod-2 ──┼──> carts-db (1 replica) ← BOTTLENECK!
carts-pod-3 ──┘
```

The database becomes the bottleneck because:
1. All pods compete for database connections
2. Database has limited connection pool
3. Database has limited CPU/memory
4. Database has limited disk I/O

## How to Detect Database Bottlenecks

### Method 1: Check Database CPU/Memory
If database CPU is high while service CPU is low, database is the bottleneck.

```powershell
# Check database resource usage
kubectl top pods -n sock-shop | Select-String "db"
```

### Method 2: Check Service Latency vs Replica Count
If latency stays high even after scaling services, database is likely the bottleneck.

### Method 3: Check Error Patterns
Errors like:
- "Connection pool exhausted"
- "Too many connections"
- "Database timeout"
- "Lock wait timeout"

These indicate database bottleneck.

### Method 4: Compare Service CPU vs Database CPU
```powershell
# Service CPU
kubectl top pods -n sock-shop | Select-String "carts-[^d]"

# Database CPU
kubectl top pods -n sock-shop | Select-String "carts-db"
```

If service CPU is low but database CPU is high → database bottleneck.

## Your Sock Shop Architecture

### Services with Databases
| Service | Database | Type | Shared? |
|---------|----------|------|---------|
| carts | carts-db | MongoDB | No (dedicated) |
| orders | orders-db | MySQL | No (dedicated) |
| catalogue | catalogue-db | MySQL | No (dedicated) |
| user | user-db | MongoDB | No (dedicated) |
| front-end | session-db | Redis | Shared with other services |

### Services WITHOUT Databases
| Service | Storage |
|---------|---------|
| payment | Stateless (no DB) |
| shipping | Stateless (no DB) |

## Should You Have Scaled Databases?

### Short Answer: IT DEPENDS

**For Read-Heavy Workloads**: Yes, scale databases
- Multiple read replicas can handle more queries
- Sock Shop is mostly read-heavy (browsing, viewing)

**For Write-Heavy Workloads**: Scaling is complex
- Can't easily scale writes across multiple instances
- Need master-slave replication or sharding
- Sock Shop has some writes (add to cart, checkout)

### Your Specific Case

Looking at your errors from the test:
```
164 × POST add_to_cart (500 Internal Server Error)
104 × POST checkout (500 Internal Server Error)
37 × DELETE clear_cart (500 Internal Server Error)
```

These are ALL database operations:
- `add_to_cart` → writes to carts-db (MongoDB)
- `checkout` → writes to orders-db (MySQL)
- `clear_cart` → writes to carts-db (MongoDB)

**This strongly suggests database bottlenecks!**

## Should Databases Be Treated Like Services?

### NO - Here's Why:

**1. Different Scaling Characteristics**
- Services: Stateless, scale horizontally easily
- Databases: Stateful, scaling is complex

**2. Different Metrics**
- Services: Scale based on RPS, latency, CPU
- Databases: Scale based on connections, query time, disk I/O

**3. Different Scaling Strategies**
- Services: Add replicas freely
- Databases: Need replication setup, data consistency

**4. Your ML Models Are Trained on Service Metrics**
- Models predict based on service RPS, latency, CPU
- Models don't see database metrics
- Can't predict database bottlenecks

### What You SHOULD Have Done:

**Option A: Pre-scale Databases (Simple)**
- Start with 2-3 database replicas
- Ensures databases aren't the bottleneck
- Focuses test on service autoscaling

**Option B: Monitor Database Metrics (Complex)**
- Collect database CPU, connections, query time
- Add database scaling logic (separate from ML)
- More realistic but much more complex

**Option C: Use Managed Databases (Production)**
- Cloud SQL, MongoDB Atlas, etc.
- Auto-scaling built-in
- Not applicable for your research

## How to Test if Databases Are the Bottleneck

### Experiment: Pre-scale Databases

**Hypothesis**: If we scale databases to 3 replicas, service scaling will be more effective.

**Test Procedure**:
1. Scale all databases to 3 replicas
2. Run 20-minute proactive test with 150 users
3. Measure violation rate over time
4. Compare to test with 1 database replica

**Expected Results**:
- **If databases were bottleneck**: Violation rate drops significantly, system converges
- **If databases weren't bottleneck**: No significant change

### Implementation

```powershell
# Scale databases to 3 replicas
kubectl scale deployment carts-db -n sock-shop --replicas=3
kubectl scale deployment orders-db -n sock-shop --replicas=3
kubectl scale deployment catalogue-db -n sock-shop --replicas=3
kubectl scale deployment user-db -n sock-shop --replicas=3

# Note: session-db (Redis) is already scaled appropriately
```

## Current Database Status

Let me check your current database setup:
