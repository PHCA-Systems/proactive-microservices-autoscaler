import json

print("\n--- PROACTIVE TIMELINE ---")
with open('kafka-structured/experiments/results/diag_proactive_step_run2001.jsonl') as f:
    for l in f:
        d = json.loads(l)
        if d.get('phase') == 'settle': continue
        front = d['services']['front-end']
        carts = d['services']['carts']
        orders = d['services']['orders']
        print(f"I={d['interval_idx']:2d} | front: {front['replicas']}r (p95:{front['p95_ms']:6.1f} cpu:{front['cpu_pct']:5.1f}%) | carts: {carts['replicas']}r (p95:{carts['p95_ms']:6.1f} cpu:{carts['cpu_pct']:5.1f}%) | orders: {orders['replicas']}r (p95:{orders['p95_ms']:6.1f} cpu:{orders['cpu_pct']:5.1f}%)")

print("\n--- REACTIVE TIMELINE ---")
with open('kafka-structured/experiments/results/diag_reactive_step_run2001.jsonl') as f:
    for l in f:
        d = json.loads(l)
        if d.get('phase') == 'settle': continue
        front = d['services']['front-end']
        carts = d['services']['carts']
        orders = d['services']['orders']
        print(f"I={d['interval_idx']:2d} | front: {front['replicas']}r (p95:{front['p95_ms']:6.1f} cpu:{front['cpu_pct']:5.1f}%) | carts: {carts['replicas']}r (p95:{carts['p95_ms']:6.1f} cpu:{carts['cpu_pct']:5.1f}%) | orders: {orders['replicas']}r (p95:{orders['p95_ms']:6.1f} cpu:{orders['cpu_pct']:5.1f}%)")
