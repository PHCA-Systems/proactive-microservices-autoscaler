#!/usr/bin/env python3
import json
from datetime import datetime

with open('results/proactive_constant_run01.jsonl', 'r') as f:
    lines = f.readlines()

# Get first, interval 33, and interval 34 timestamps
snap1 = json.loads(lines[0])
snap33 = json.loads(lines[32])
snap34 = json.loads(lines[33])

t1 = datetime.fromisoformat(snap1['timestamp'])
t33 = datetime.fromisoformat(snap33['timestamp'])
t34 = datetime.fromisoformat(snap34['timestamp'])

elapsed_33 = (t33 - t1).total_seconds() / 60
elapsed_34 = (t34 - t1).total_seconds() / 60

print(f'Interval 1:  {snap1["timestamp"]}')
print(f'Interval 33: {snap33["timestamp"]} (elapsed: {elapsed_33:.1f} min)')
print(f'Interval 34: {snap34["timestamp"]} (elapsed: {elapsed_34:.1f} min)')
print()
print(f'Load appears to stop between intervals 33 and 34')
print(f'That is at approximately {elapsed_33:.1f} minutes into the test')
print()
print('Expected: Load should run for 20 minutes')
print(f'Actual: Load ran for ~{elapsed_33:.1f} minutes')
