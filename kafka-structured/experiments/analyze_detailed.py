#!/usr/bin/env python3
"""Detailed analysis of convergence test"""
import json

# Load proactive results
print('='*70)
print('PROACTIVE SYSTEM - Service Details')
print('='*70)
with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()
    
    # Show intervals 1, 20, 40
    for idx in [0, 19, 39]:
        snap = json.loads(lines[idx])
        print(f"\nInterval {idx+1}:")
        for svc, metrics in snap['services'].items():
            violated = "VIOLATED" if metrics['slo_violated'] else "OK"
            print(f"  {svc:12s}: {metrics['replicas']} replicas, p95={metrics['p95_ms']:.1f}ms [{violated}]")

print('\n' + '='*70)
print('REACTIVE SYSTEM - Service Details')
print('='*70)
with open('results/reactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()
    
    # Show intervals 1, 20, 40
    for idx in [0, 19, 39]:
        snap = json.loads(lines[idx])
        print(f"\nInterval {idx+1}:")
        for svc, metrics in snap['services'].items():
            violated = "VIOLATED" if metrics['slo_violated'] else "OK"
            print(f"  {svc:12s}: {metrics['replicas']} replicas, p95={metrics['p95_ms']:.1f}ms [{violated}]")
