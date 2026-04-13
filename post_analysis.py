import json
from pathlib import Path

MONITORED_SERVICES = ['front-end', 'carts', 'orders', 'catalogue', 'user', 'payment', 'shipping']

RESULTS_DIR = Path('kafka-structured/experiments/results')
pro_file = RESULTS_DIR / 'diag_proactive_step_run2001.jsonl'
rea_file = RESULTS_DIR / 'diag_reactive_step_run2001.jsonl'

def load(fp):
    return [json.loads(line) for line in open(fp) if json.loads(line).get('phase') != 'settle']

pro_load = load(pro_file)
rea_load = load(rea_file)

print('\n' + '='*70)
print('  HEAD-TO-HEAD COMPARISON')
print('='*70)

print(f"\n  {'Service':<12} | {'Proactive VR%':>14} | {'Reactive VR%':>14} | {'Pro avg p95':>12} | {'Rea avg p95':>12} | {'Winner':>8}")
print('  ' + '-' * 85)

for svc in MONITORED_SERVICES:
    pro_viol = sum(1 for s in pro_load if s['services'][svc]['slo_violated'])
    rea_viol = sum(1 for s in rea_load if s['services'][svc]['slo_violated'])
    pro_vr = (pro_viol / len(pro_load) * 100) if pro_load else 0
    rea_vr = (rea_viol / len(rea_load) * 100) if rea_load else 0

    pro_p95 = [s['services'][svc]['p95_ms'] for s in pro_load if s['services'][svc]['p95_ms'] > 0]
    rea_p95 = [s['services'][svc]['p95_ms'] for s in rea_load if s['services'][svc]['p95_ms'] > 0]
    pro_avg = sum(pro_p95)/len(pro_p95) if pro_p95 else 0
    rea_avg = sum(rea_p95)/len(rea_p95) if rea_p95 else 0

    winner = 'TIE'    
    if pro_vr < rea_vr:
        winner = 'PRO (W)'
    elif rea_vr < pro_vr:
        winner = 'REA (W)'
    elif pro_avg < rea_avg and abs(pro_avg - rea_avg) > 2.0:
        winner = 'PRO (W)*' 
    elif rea_avg < pro_avg and abs(pro_avg - rea_avg) > 2.0:
        winner = 'REA (W)*' 

    print(f"  {svc:<12} | {pro_vr:13.1f}% | {rea_vr:13.1f}% | {pro_avg:10.1f}ms | {rea_avg:10.1f}ms | {winner:>8}")

pro_total_viol = sum(1 for s in pro_load for svc in MONITORED_SERVICES if s['services'][svc]['slo_violated'])
rea_total_viol = sum(1 for s in rea_load for svc in MONITORED_SERVICES if s['services'][svc]['slo_violated'])
pro_total = len(pro_load) * len(MONITORED_SERVICES)
rea_total = len(rea_load) * len(MONITORED_SERVICES)

print(f"\n  TOTAL:  Proactive {pro_total_viol}/{pro_total} ({pro_total_viol/pro_total*100:.1f}%)  vs  Reactive {rea_total_viol}/{rea_total} ({rea_total_viol/rea_total*100:.1f}%)")
