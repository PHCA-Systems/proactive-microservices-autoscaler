#!/usr/bin/env python3
"""Analyze convergence test results"""
import json

# Load proactive results
proactive_violations = []
proactive_replicas = []
with open('results/proactive_constant_run01.jsonl', 'r') as f:
    for line in f:
        snap = json.loads(line)
        violations = sum(1 for svc in snap['services'].values() if svc['slo_violated'])
        total_replicas = sum(svc['replicas'] for svc in snap['services'].values())
        proactive_violations.append(violations)
        proactive_replicas.append(total_replicas)

# Load reactive results
reactive_violations = []
reactive_replicas = []
with open('results/reactive_constant_run01.jsonl', 'r') as f:
    for line in f:
        snap = json.loads(line)
        violations = sum(1 for svc in snap['services'].values() if svc['slo_violated'])
        total_replicas = sum(svc['replicas'] for svc in snap['services'].values())
        reactive_violations.append(violations)
        reactive_replicas.append(total_replicas)

# Calculate metrics
def analyze_phase(violations, start, end):
    phase_violations = violations[start:end]
    avg = sum(phase_violations) / len(phase_violations)
    pct = (avg / 7) * 100
    return avg, pct

print('='*70)
print('CONVERGENCE TEST ANALYSIS: 20-Minute Constant Load (150 users)')
print('='*70)
print()
print('PROACTIVE SYSTEM:')
print('-' * 70)
early_avg, early_pct = analyze_phase(proactive_violations, 0, 10)
mid_avg, mid_pct = analyze_phase(proactive_violations, 10, 30)
late_avg, late_pct = analyze_phase(proactive_violations, 30, 40)
print(f'  Early phase (0-5 min):    {early_avg:.1f}/7 services violating ({early_pct:.1f}%)')
print(f'  Mid phase (5-15 min):     {mid_avg:.1f}/7 services violating ({mid_pct:.1f}%)')
print(f'  Late phase (15-20 min):   {late_avg:.1f}/7 services violating ({late_pct:.1f}%)')
print(f'  Final replica count:      {proactive_replicas[-1]} total')
converged_p = "YES" if late_avg < 0.7 else "NO"
print(f'  Convergence achieved:     {converged_p}')
print()
print('REACTIVE SYSTEM (HPA):')
print('-' * 70)
early_avg_r, early_pct_r = analyze_phase(reactive_violations, 0, 10)
mid_avg_r, mid_pct_r = analyze_phase(reactive_violations, 10, 30)
late_avg_r, late_pct_r = analyze_phase(reactive_violations, 30, 40)
print(f'  Early phase (0-5 min):    {early_avg_r:.1f}/7 services violating ({early_pct_r:.1f}%)')
print(f'  Mid phase (5-15 min):     {mid_avg_r:.1f}/7 services violating ({mid_pct_r:.1f}%)')
print(f'  Late phase (15-20 min):   {late_avg_r:.1f}/7 services violating ({late_pct_r:.1f}%)')
print(f'  Final replica count:      {reactive_replicas[-1]} total')
converged_r = "YES" if late_avg_r < 0.7 else "NO"
print(f'  Convergence achieved:     {converged_r}')
print()
print('COMPARISON:')
print('-' * 70)
faster = "YES" if late_pct < late_pct_r else "NO"
fewer = "YES" if proactive_replicas[-1] < reactive_replicas[-1] else "NO"
print(f'  Proactive converges faster:    {faster}')
print(f'  Proactive uses fewer replicas: {fewer} ({proactive_replicas[-1]} vs {reactive_replicas[-1]})')
print(f'  Improvement in final violations: {late_pct_r - late_pct:.1f}% reduction')
print()
print('DETAILED TIMELINE:')
print('-' * 70)
print('Interval | Proactive Violations | Reactive Violations')
print('---------+---------------------+--------------------')
for i in range(40):
    print(f'  {i+1:2d}     |        {proactive_violations[i]}/7          |        {reactive_violations[i]}/7')
