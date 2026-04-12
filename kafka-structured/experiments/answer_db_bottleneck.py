#!/usr/bin/env python3
"""
Answer: Were databases the bottleneck preventing p95 from improving as replicas increased?
"""
import json

print("="*80)
print("QUESTION: Were databases the bottleneck?")
print("="*80)
print()
print("Method: Compare p95 latency at different replica counts for carts and orders")
print("If databases were the bottleneck, p95 should NOT improve as replicas increase")
print()

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()

# Analyze carts service
print("CARTS SERVICE (uses carts-db):")
print("-"*80)
print("Replicas | Intervals | Avg P95 | Min P95 | Max P95 | Improvement from 1 replica")
print("---------|-----------|---------|---------|---------|---------------------------")

carts_by_replicas = {}
for i in range(0, 31):  # Only valid snapshots
    snap = json.loads(lines[i])
    replicas = snap['services']['carts']['replicas']
    p95 = snap['services']['carts']['p95_ms']
    if replicas not in carts_by_replicas:
        carts_by_replicas[replicas] = []
    carts_by_replicas[replicas].append(p95)

baseline_avg = sum(carts_by_replicas[1]) / len(carts_by_replicas[1])
for replicas in sorted(carts_by_replicas.keys()):
    latencies = carts_by_replicas[replicas]
    avg = sum(latencies) / len(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    improvement = ((baseline_avg - avg) / baseline_avg) * 100
    print(f"   {replicas}     |    {len(latencies):2d}     | {avg:6.1f}ms | {min_lat:6.1f}ms | {max_lat:6.1f}ms | {improvement:+6.1f}%")

print()
print("ORDERS SERVICE (uses orders-db):")
print("-"*80)
print("Replicas | Intervals | Avg P95 | Min P95 | Max P95 | Improvement from 1 replica")
print("---------|-----------|---------|---------|---------|---------------------------")

orders_by_replicas = {}
for i in range(0, 31):
    snap = json.loads(lines[i])
    replicas = snap['services']['orders']['replicas']
    p95 = snap['services']['orders']['p95_ms']
    if replicas not in orders_by_replicas:
        orders_by_replicas[replicas] = []
    orders_by_replicas[replicas].append(p95)

baseline_avg = sum(orders_by_replicas[1]) / len(orders_by_replicas[1])
for replicas in sorted(orders_by_replicas.keys()):
    latencies = orders_by_replicas[replicas]
    avg = sum(latencies) / len(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    improvement = ((baseline_avg - avg) / baseline_avg) * 100
    print(f"   {replicas}     |    {len(latencies):2d}     | {avg:6.1f}ms | {min_lat:6.1f}ms | {max_lat:6.1f}ms | {improvement:+6.1f}%")

print()
print("FRONT-END SERVICE (no database, for comparison):")
print("-"*80)
print("Replicas | Intervals | Avg P95 | Min P95 | Max P95 | Improvement from 2 replicas")
print("---------|-----------|---------|---------|---------|----------------------------")

fe_by_replicas = {}
for i in range(0, 31):
    snap = json.loads(lines[i])
    replicas = snap['services']['front-end']['replicas']
    p95 = snap['services']['front-end']['p95_ms']
    if replicas not in fe_by_replicas:
        fe_by_replicas[replicas] = []
    fe_by_replicas[replicas].append(p95)

baseline_avg = sum(fe_by_replicas[2]) / len(fe_by_replicas[2])
for replicas in sorted(fe_by_replicas.keys()):
    latencies = fe_by_replicas[replicas]
    avg = sum(latencies) / len(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    improvement = ((baseline_avg - avg) / baseline_avg) * 100
    print(f"   {replicas}     |    {len(latencies):2d}     | {avg:6.1f}ms | {min_lat:6.1f}ms | {max_lat:6.1f}ms | {improvement:+6.1f}%")

print()
print("="*80)
print("ANSWER:")
print("="*80)

# Check if scaling helped
carts_improved = ((baseline_avg - sum(carts_by_replicas[5]) / len(carts_by_replicas[5])) / baseline_avg) * 100
orders_baseline = sum(orders_by_replicas[1]) / len(orders_by_replicas[1])
orders_final = sum(orders_by_replicas[5]) / len(orders_by_replicas[5])
orders_improved = ((orders_baseline - orders_final) / orders_baseline) * 100

print()
if carts_improved < 20 and orders_improved < 0:
    print("YES - Databases were the bottleneck!")
    print()
    print("Evidence:")
    print(f"  - Carts: Scaling 1->5 replicas only improved p95 by {carts_improved:.1f}%")
    print(f"  - Orders: Scaling 1->5 replicas WORSENED p95 by {abs(orders_improved):.1f}%")
    print(f"  - Front-end: Scaling 2->5 replicas improved p95 by {((baseline_avg - sum(fe_by_replicas[5]) / len(fe_by_replicas[5])) / baseline_avg) * 100:.1f}%")
    print()
    print("Conclusion: When databases (carts-db=2, orders-db=1) are bottlenecked,")
    print("scaling the application tier has minimal or negative effect on latency.")
    print()
    print("NOTE: This test had carts-db=2 and orders-db=1 replicas.")
    print("To confirm, we need to re-run with carts-db=3 and orders-db=3.")
else:
    print("NO - Databases were NOT the primary bottleneck")
    print()
    print("Evidence:")
    print(f"  - Carts improved by {carts_improved:.1f}%")
    print(f"  - Orders improved by {orders_improved:.1f}%")
