#!/usr/bin/env python3
"""
Compare: Does scaling databases allow service scaling to improve p95?
"""
import json

print("="*80)
print("COMPARISON: With vs Without Database Scaling")
print("="*80)
print()

# OLD TEST: databases NOT scaled (carts-db=2, orders-db=1)
print("TEST 1: WITHOUT Database Scaling (from earlier 20-min test)")
print("  carts-db: 2 replicas, orders-db: 1 replica")
print("-"*80)

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines_old = f.readlines()

# Only use first 10 snapshots for fair comparison
print("\nCARTS (first 10 intervals):")
carts_old = {}
for i in range(0, min(10, len(lines_old))):
    snap = json.loads(lines_old[i])
    replicas = snap['services']['carts']['replicas']
    p95 = snap['services']['carts']['p95_ms']
    if replicas not in carts_old:
        carts_old[replicas] = []
    carts_old[replicas].append(p95)

for replicas in sorted(carts_old.keys()):
    avg = sum(carts_old[replicas]) / len(carts_old[replicas])
    print(f"  {replicas} replicas: {avg:.1f}ms avg p95 ({len(carts_old[replicas])} samples)")

print("\nORDERS (first 10 intervals):")
orders_old = {}
for i in range(0, min(10, len(lines_old))):
    snap = json.loads(lines_old[i])
    replicas = snap['services']['orders']['replicas']
    p95 = snap['services']['orders']['p95_ms']
    if replicas not in orders_old:
        orders_old[replicas] = []
    orders_old[replicas].append(p95)

for replicas in sorted(orders_old.keys()):
    avg = sum(orders_old[replicas]) / len(orders_old[replicas])
    print(f"  {replicas} replicas: {avg:.1f}ms avg p95 ({len(orders_old[replicas])} samples)")

# Check if new test file exists and has valid data
import os
new_file = 'results/proactive_constant_run01.jsonl'
if os.path.getmtime(new_file) > os.path.getmtime('results/proactive_constant_run5000.jsonl'):
    print("\n" + "="*80)
    print("TEST 2: WITH Database Scaling (from recent 6-min test)")
    print("  carts-db: 3 replicas, orders-db: 3 replicas")
    print("-"*80)
    
    # The file was overwritten, so this IS the new test
    # But we need to check if it has valid data (Prometheus timeouts)
    with open(new_file, 'r') as f:
        lines_new = f.readlines()
    
    # Check for valid data
    snap = json.loads(lines_new[0])
    if snap['services']['carts']['p95_ms'] == 0.0:
        print("\nWARNING: New test has invalid data (Prometheus timeouts)")
        print("Cannot compare - need to re-run test")
    else:
        print("\nCARTS (all intervals):")
        carts_new = {}
        for i in range(0, len(lines_new)):
            snap = json.loads(lines_new[i])
            replicas = snap['services']['carts']['replicas']
            p95 = snap['services']['carts']['p95_ms']
            if p95 > 0:  # Skip zero values from timeouts
                if replicas not in carts_new:
                    carts_new[replicas] = []
                carts_new[replicas].append(p95)
        
        for replicas in sorted(carts_new.keys()):
            avg = sum(carts_new[replicas]) / len(carts_new[replicas])
            print(f"  {replicas} replicas: {avg:.1f}ms avg p95 ({len(carts_new[replicas])} samples)")
        
        print("\nORDERS (all intervals):")
        orders_new = {}
        for i in range(0, len(lines_new)):
            snap = json.loads(lines_new[i])
            replicas = snap['services']['orders']['replicas']
            p95 = snap['services']['orders']['p95_ms']
            if p95 > 0:
                if replicas not in orders_new:
                    orders_new[replicas] = []
                orders_new[replicas].append(p95)
        
        for replicas in sorted(orders_new.keys()):
            avg = sum(orders_new[replicas]) / len(orders_new[replicas])
            print(f"  {replicas} replicas: {avg:.1f}ms avg p95 ({len(orders_new[replicas])} samples)")
        
        print("\n" + "="*80)
        print("CONCLUSION:")
        print("="*80)
        
        # Compare improvement
        if len(carts_new) > 1 and len(orders_new) > 1:
            carts_old_max = max(carts_old.keys())
            carts_new_max = max(carts_new.keys())
            
            if carts_old_max in carts_old and carts_new_max in carts_new:
                old_improvement = ((sum(carts_old[1])/len(carts_old[1]) - sum(carts_old[carts_old_max])/len(carts_old[carts_old_max])) / (sum(carts_old[1])/len(carts_old[1]))) * 100
                new_improvement = ((sum(carts_new[1])/len(carts_new[1]) - sum(carts_new[carts_new_max])/len(carts_new[carts_new_max])) / (sum(carts_new[1])/len(carts_new[1]))) * 100
                
                print(f"\nCarts scaling effectiveness:")
                print(f"  Without DB scaling: {old_improvement:+.1f}% improvement")
                print(f"  With DB scaling: {new_improvement:+.1f}% improvement")
                
                if new_improvement > old_improvement + 10:
                    print("\n  RESULT: Database scaling HELPED! Service scaling now more effective.")
                else:
                    print("\n  RESULT: Database scaling had minimal effect.")
else:
    print("\n" + "="*80)
    print("New test file not found or older than reference test")
    print("="*80)
