#!/usr/bin/env python3
import json
from datetime import datetime, timedelta

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()

# Parse first snapshot to establish baseline
snap1 = json.loads(lines[0])
t_first_snapshot = datetime.fromisoformat(snap1['timestamp'])

# The experiment does: reset_cluster() which includes 120s wait, THEN starts Locust
# First snapshot is collected 30s AFTER Locust starts
# So Locust started 30s before first snapshot
t_locust_start = t_first_snapshot - timedelta(seconds=30)

print("TIMING ANALYSIS")
print("="*80)
print(f"Locust started at:        {t_locust_start.strftime('%H:%M:%S')}")
print(f"First snapshot at:        {t_first_snapshot.strftime('%H:%M:%S')} (0:30 elapsed)")
print()

# Locust was configured to run for 20 minutes
t_locust_should_stop = t_locust_start + timedelta(minutes=20)
print(f"Locust should stop at:    {t_locust_should_stop.strftime('%H:%M:%S')} (20:00 elapsed)")
print()

# Check snapshots 30-40
print("SNAPSHOT TIMING vs LOAD STATUS:")
print("-"*80)
print("Snap | Clock Time | Elapsed | Load Status        | front-end | carts | orders")
print("-----|------------|---------|--------------------|-----------| ------|--------")

for i in range(30, 40):
    snap = json.loads(lines[i])
    t = datetime.fromisoformat(snap['timestamp'])
    elapsed = (t - t_locust_start).total_seconds() / 60
    
    # Determine if load should be active
    if t < t_locust_should_stop:
        status = "LOAD ACTIVE"
    else:
        status = "LOAD STOPPED"
    
    fe = snap['services']['front-end']['p95_ms']
    carts = snap['services']['carts']['p95_ms']
    orders = snap['services']['orders']['p95_ms']
    
    print(f" {i+1:2d}  | {t.strftime('%H:%M:%S')} | {elapsed:5.1f}m | {status:18s} | {fe:7.1f}ms | {carts:5.1f}ms | {orders:6.1f}ms")

print()
print("CONCLUSION:")
print("-"*80)

snap33 = json.loads(lines[32])
snap34 = json.loads(lines[33])
t33 = datetime.fromisoformat(snap33['timestamp'])
t34 = datetime.fromisoformat(snap34['timestamp'])

if t33 < t_locust_should_stop and t34 > t_locust_should_stop:
    print(f"Snapshot 33 collected at {t33.strftime('%H:%M:%S')} - BEFORE Locust stopped")
    print(f"Snapshot 34 collected at {t34.strftime('%H:%M:%S')} - AFTER Locust stopped")
    print()
    print("The latency drop at snapshot 34 is EXPECTED because Locust stopped between")
    print("snapshots 33 and 34.")
elif t34 < t_locust_should_stop:
    print(f"Snapshot 34 collected at {t34.strftime('%H:%M:%S')} - BEFORE Locust should stop")
    print(f"But latencies dropped to near-zero, indicating Locust stopped early.")
    print()
    print("PROBLEM: Locust stopped approximately 3 minutes early!")
    print("This suggests either:")
    print("  1. The --run-time flag is being interpreted differently")
    print("  2. The LoadTestShape is stopping early")
    print("  3. Locust crashed or was killed")
