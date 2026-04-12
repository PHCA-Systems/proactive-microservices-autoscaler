#!/usr/bin/env python3
"""Investigate if scaling actually improves p95 latency"""
import json

print("="*80)
print("SCALING EFFECTIVENESS ANALYSIS")
print("="*80)
print()

# Analyze proactive test
print("PROACTIVE SYSTEM - Does scaling reduce latency?")
print("-"*80)

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()

# Focus on the services that kept violating: carts and orders
print("\nCARTS SERVICE:")
print("Interval | Replicas | P95 Latency | Violated | Notes")
print("---------|----------|-------------|----------|------------------")
for i in range(0, 31):  # Only valid snapshots
    snap = json.loads(lines[i])
    carts = snap['services']['carts']
    violated = "YES" if carts['slo_violated'] else "NO"
    note = ""
    if i > 0:
        prev = json.loads(lines[i-1])['services']['carts']
        if carts['replicas'] > prev['replicas']:
            note = f"SCALED UP from {prev['replicas']}"
    print(f"  {i+1:2d}     |    {carts['replicas']}     | {carts['p95_ms']:7.1f} ms  |   {violated:3s}    | {note}")

print("\nORDERS SERVICE:")
print("Interval | Replicas | P95 Latency | Violated | Notes")
print("---------|----------|-------------|----------|------------------")
for i in range(0, 31):
    snap = json.loads(lines[i])
    orders = snap['services']['orders']
    violated = "YES" if orders['slo_violated'] else "NO"
    note = ""
    if i > 0:
        prev = json.loads(lines[i-1])['services']['orders']
        if orders['replicas'] > prev['replicas']:
            note = f"SCALED UP from {prev['replicas']}"
    print(f"  {i+1:2d}     |    {orders['replicas']}     | {orders['p95_ms']:7.1f} ms  |   {violated:3s}    | {note}")

print("\nFRONT-END SERVICE:")
print("Interval | Replicas | P95 Latency | Violated | Notes")
print("---------|----------|-------------|----------|------------------")
for i in range(0, 31):
    snap = json.loads(lines[i])
    fe = snap['services']['front-end']
    violated = "YES" if fe['slo_violated'] else "NO"
    note = ""
    if i > 0:
        prev = json.loads(lines[i-1])['services']['front-end']
        if fe['replicas'] > prev['replicas']:
            note = f"SCALED UP from {prev['replicas']}"
    print(f"  {i+1:2d}     |    {fe['replicas']}     | {fe['p95_ms']:7.1f} ms  |   {violated:3s}    | {note}")

# Calculate correlation
print("\n" + "="*80)
print("CORRELATION ANALYSIS")
print("="*80)

services_to_check = ['carts', 'orders', 'front-end']
for svc in services_to_check:
    print(f"\n{svc.upper()}:")
    
    # Group by replica count and calculate average p95
    replica_latencies = {}
    for i in range(0, 31):
        snap = json.loads(lines[i])
        replicas = snap['services'][svc]['replicas']
        p95 = snap['services'][svc]['p95_ms']
        if replicas not in replica_latencies:
            replica_latencies[replicas] = []
        replica_latencies[replicas].append(p95)
    
    print("  Replicas | Avg P95 | Min P95 | Max P95 | Samples")
    print("  ---------|---------|---------|---------|--------")
    for replicas in sorted(replica_latencies.keys()):
        latencies = replica_latencies[replicas]
        avg = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"     {replicas}     | {avg:6.1f}ms | {min_lat:6.1f}ms | {max_lat:6.1f}ms |   {len(latencies)}")
    
    # Check if scaling helps
    if len(replica_latencies) > 1:
        replica_counts = sorted(replica_latencies.keys())
        avg_at_min = sum(replica_latencies[replica_counts[0]]) / len(replica_latencies[replica_counts[0]])
        avg_at_max = sum(replica_latencies[replica_counts[-1]]) / len(replica_latencies[replica_counts[-1]])
        improvement = ((avg_at_min - avg_at_max) / avg_at_min) * 100
        print(f"  Scaling from {replica_counts[0]} to {replica_counts[-1]} replicas: {improvement:+.1f}% change")
        if improvement < 0:
            print(f"  WARNING: Latency INCREASED with more replicas!")

print("\n" + "="*80)
print("HYPOTHESIS: Database bottleneck?")
print("="*80)
print("\nCarts and orders both use databases (carts-db, orders-db).")
print("If databases are bottlenecked, scaling the service won't help.")
print("\nChecking database replica counts...")

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    snap = json.loads(f.readline())
    
# Check if we're tracking database services
if 'carts-db' in snap['services']:
    print("\nDatabase services are being tracked.")
else:
    print("\nDatabase services are NOT in monitored services list!")
    print("This is likely the problem - databases are single replicas and bottlenecked.")
