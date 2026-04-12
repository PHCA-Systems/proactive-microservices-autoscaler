# Scaling Failure Analysis: Why Both Systems Show 90% Violations

## You're Absolutely Right

The whole point of autoscaling is to add replicas so the system handles 150 users with the same latency as 50 users. If both proactive and reactive show 90% violations, **neither system is scaling effectively**.

## Critical Findings

### 1. PROACTIVE: Scales Too Slowly, Wrong Services

**Front-end scaling (the bottleneck):**
- Interval 0-3: 1 replica, p95 = 50-67ms (40-87% over SLO)
- Interval 4: Scales to 2 replicas → p95 drops to 45ms (still 25% over)
- Interval 5-12: Stays at 2 replicas → p95 = 25-35ms (mostly OK)
- Interval 13: Scales to 3 replicas → p95 = 18-27ms (finally good!)

**Problem**: Takes 13 intervals (6.5 minutes) to reach adequate front-end capacity!

**Carts/Orders scaling (over-aggressive):**
- Interval 0-8: 2 replicas, still violating
- Interval 9: Scales to 3 replicas
- Interval 10: Carts p95 = 650ms (!), Orders p95 = 180ms (massive spike)
- Interval 17: Scales to 4 replicas

**Problem**: Scales carts/orders aggressively but they STILL violate throughout the test.

### 2. REACTIVE: Scales Front-end Quickly, But Carts/Orders Stuck

**Front-end scaling (good):**
- Interval 0-1: 1 replica, p95 = 60-70ms (violating)
- Interval 2: Scales to 2 replicas → p95 drops to 25ms (good!)
- Interval 3-19: Stays at 2 replicas, p95 = 22-27ms (consistently good)

**Carts/Orders (stuck at 1 replica):**
- Interval 0-17: Stays at 1 replica
- p95 = 45-48ms throughout (consistently violating)
- Interval 12-15: Orders p95 spikes to 981-1112ms (catastrophic!)

**Shipping (bizarre behavior):**
- Interval 11: Suddenly scales from 1 to 10 replicas (!)
- Interval 12-13: Shipping p95 = 432-737ms (massive degradation)
- This is clearly a bug - reactive HPA shouldn't scale shipping to 10 replicas

### 3. Why Carts/Orders Keep Violating

Looking at the p95 latency values:
- Carts: 45-73ms (consistently 25-100% over 36ms SLO)
- Orders: 45-114ms (consistently 25-200% over 36ms SLO)

These services are violating even with 2-3 replicas because:
1. They have database dependencies (MongoDB for carts, MySQL for orders)
2. Adding replicas doesn't help if the database is the bottleneck
3. The 36ms SLO may be too aggressive for services with database calls

### 4. CPU Usage Patterns

**Proactive - Interval 1 (high violations):**
- Front-end: 18% CPU, 1 replica → should scale
- Carts: 172% CPU, 2 replicas → heavily overloaded!
- Orders: 162% CPU, 2 replicas → heavily overloaded!

**Proactive - Interval 10 (carts spike):**
- Carts: 199% CPU, 3 replicas → still overloaded!
- Orders: 174% CPU, 3 replicas → still overloaded!

**Reactive - Interval 1 (before scaling):**
- Front-end: 21% CPU, 1 replica
- Carts: 23% CPU, 1 replica
- Orders: 11% CPU, 1 replica

The CPU usage is relatively low, which explains why reactive HPA doesn't scale carts/orders - it's using CPU-based thresholds, not latency!

## Root Causes

### 1. Proactive ML Models Are Trained on 50-User Load
The ML models learned patterns from 50-user constant load where:
- Front-end p95 = 32-37ms (comfortable)
- Carts/Orders p95 = ~30-40ms (comfortable)

With 150 users (3x load), the feature distributions are completely different:
- RPS is 3x higher
- Latency is 2x higher
- CPU patterns are different

**The models are predicting outside their training distribution.**

### 2. Reactive HPA Uses CPU Thresholds, Not Latency
Reactive HPA scales based on CPU utilization (typically 50-80% threshold).

Looking at the data:
- Carts at 1 replica: 20-23% CPU → HPA thinks it's fine!
- Orders at 1 replica: 6-14% CPU → HPA thinks it's fine!

But latency is violating because:
- Database calls dominate latency, not CPU
- Network latency adds overhead
- Request queuing happens before CPU saturation

**HPA can't see the latency violations.**

### 3. Database Bottlenecks
Carts and Orders have persistent violations even with multiple replicas:
- Carts → MongoDB (session-db)
- Orders → MySQL (orders-db)

Adding replicas doesn't help if the database is the bottleneck. All replicas share the same database instance.

### 4. 36ms SLO May Be Too Aggressive for 150 Users
The 36ms threshold was derived from 50-user load. With 150 users:
- More concurrent requests
- More database contention
- More network overhead
- Higher queuing delays

The system may physically cannot maintain 36ms p95 at 150 users without:
- Scaling databases (not just services)
- Optimizing database queries
- Adding caching layers
- Using connection pooling

## Why Both Show 90% Violations

**Proactive**: Scales too slowly and to wrong services. By the time it reaches adequate capacity (interval 13), most of the test is over.

**Reactive**: Scales front-end quickly but ignores carts/orders because CPU is low. Can't see latency violations.

**Both**: Can't fix database bottlenecks by scaling service replicas.

## Solutions

### Option 1: Test at 50 Users (Recommended for Comparison)
- Matches training conditions
- SLO threshold is valid
- Both systems should perform well
- Fair comparison of proactive vs reactive

### Option 2: Retrain Models for 150 Users
- Collect new training data at 150 users
- Derive new SLO threshold (probably 50-60ms)
- Retrain all ML models
- Time-consuming but academically sound

### Option 3: Fix the Scaling Logic
**For Proactive:**
- Investigate why front-end scales so slowly
- Check ML model predictions - are they predicting SCALE_UP?
- Check consensus service - is it aggregating votes correctly?
- Check if there's a cooldown preventing scaling

**For Reactive:**
- Switch HPA from CPU-based to custom metrics (latency-based)
- Or accept that HPA can't handle latency SLOs

**For Both:**
- Scale databases, not just services
- Add database connection pooling
- Optimize database queries
- Consider caching layer

### Option 4: Acknowledge the Limitation
In your thesis, document that:
- 36ms SLO is valid for 50-user load
- At 150 users, database bottlenecks dominate
- Scaling service replicas doesn't help with database bottlenecks
- This is a fundamental limitation of stateful microservices

## Immediate Action

I recommend checking the proactive ML predictions for the first 5 intervals:
- Are the models predicting SCALE_UP for front-end?
- Is the consensus service receiving these predictions?
- Is the authoritative scaler actually issuing scale commands?
- Is there a cooldown or rate limit preventing scaling?

Should I investigate the ML inference logs and consensus service logs from run6000?
