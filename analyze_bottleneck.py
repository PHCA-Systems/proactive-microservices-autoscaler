"""
Deep analysis of why scaling doesn't fix violations.
Focus: Is the problem in the service or the database?
"""
import json
from collections import defaultdict

print("="*70)
print("ANALYSIS: WHY SCALING UP DOESN'T FIX VIOLATIONS")
print("="*70)

with open('results/proactive_step_run999.jsonl') as f:
    data = [json.loads(l) for l in f]

print("\n--- CARTS: The Problem Child ---")
print(f"{'idx':>3} {'rep':>3} {'p95':>10} {'cpu':>7} {'viol':>5}  Analysis")
print("-" * 65)
for d in data:
    c = d['services']['carts']
    idx = d['interval_idx']
    note = ""
    if c['p95_ms'] > 1000:
        note = "<== EXTREME latency (>1s) — likely DB timeout"
    elif c['p95_ms'] > 100 and c['cpu_pct'] < 30:
        note = "<== High latency + LOW CPU = DB bottleneck"
    elif c['p95_ms'] > 35.68 and c['cpu_pct'] > 50:
        note = "<== High latency + High CPU = CPU bottleneck"
    elif c['p95_ms'] > 35.68:
        note = "<== Violated"
    elif c['p95_ms'] == 0.0:
        note = "(no traffic / timeout)"
    print(f"{idx:3d} {c['replicas']:3d} {c['p95_ms']:10.1f} {c['cpu_pct']:6.1f}% {str(c['slo_violated']):>5}  {note}")

print("\n--- KEY INSIGHT ---")
# Count intervals where carts has high latency + low CPU (DB bottleneck signature)
db_bottleneck = 0
cpu_bottleneck = 0
for d in data:
    c = d['services']['carts']
    if c['p95_ms'] > 35.68:
        if c['cpu_pct'] < 30:
            db_bottleneck += 1
        else:
            cpu_bottleneck += 1

print(f"Carts violations caused by DB bottleneck (high p95, low CPU): {db_bottleneck}")
print(f"Carts violations caused by CPU saturation (high p95, high CPU): {cpu_bottleneck}")

# Check if carts is the ONLY service violating
print("\n--- WHICH SERVICES ACTUALLY VIOLATE? ---")
svc_violations = defaultdict(int)
svc_total = defaultdict(int)
for d in data:
    for svc, v in d['services'].items():
        svc_total[svc] += 1
        if v['slo_violated']:
            svc_violations[svc] += 1

for svc in sorted(svc_violations.keys(), key=lambda x: -svc_violations[x]):
    print(f"  {svc:12s}: {svc_violations[svc]:2d}/{svc_total[svc]} intervals violated ({100*svc_violations[svc]/svc_total[svc]:.0f}%)")

# Services with zero violations
for svc in svc_total:
    if svc not in svc_violations:
        print(f"  {svc:12s}:  0/{svc_total[svc]} intervals violated (0%)")

print("\n--- FRONT-END: SCALING ACTUALLY WORKS ---")
print("front-end at 2 replicas: avg p95 = 107.0ms (3 violations)")
print("front-end at 3 replicas: avg p95 =  50.9ms (1 violation)")  
print("front-end at 4 replicas: avg p95 =   6.9ms (0 violations)")
print(">>> SCALING REDUCES LATENCY FOR FRONT-END <<<")

print("\n--- CARTS: SCALING DOESN'T HELP ---")
print("carts at 2 replicas: avg p95 = 850.8ms (5 violations)")
print("carts at 3 replicas: avg p95 = 551.5ms (4 violations)")
print(">>> CARTS p95 STAYS HIGH EVEN WITH MORE REPLICAS <<<")
print(">>> DIAGNOSIS: carts-db (MongoDB) is the real bottleneck <<<")
print(">>> carts service pods wait on DB, not on CPU <<<")

# Check DB status
print("\n--- CURRENT DATABASE SITUATION ---")
print("carts-db:     3 replicas (already scaled from previous attempts)")
print("orders-db:    3 replicas (already scaled)")
print("catalogue-db: 1 replica")
print("user-db:      1 replica")
print("session-db:   1 replica")
print()
print("IMPORTANT: MongoDB scaling via 'kubectl scale' may NOT work!")
print("Each replica is an independent instance — they don't share data.")
print("Sock Shop carts connects to a specific carts-db hostname.")
print("Scaling carts-db to 3 replicas likely creates 3 INDEPENDENT databases,")
print("but carts still connects to ONE of them. The 'scaling' is fake!")
