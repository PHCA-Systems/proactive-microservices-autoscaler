import json
from collections import defaultdict
import statistics

file_path = "kafka-structured/experiments/results/diag_reactive_step_run2001.jsonl"

data_by_svc = defaultdict(lambda: defaultdict(list))

with open(file_path, 'r') as f:
    for line in f:
        d = json.loads(line)
        if d.get("phase") == "settle":
            continue
            
        for svc in ["front-end", "carts", "orders"]:
            metrics = d["services"][svc]
            repl = metrics["replicas"]
            # Exclude intervals with zero traffic entirely
            if metrics["p95_ms"] > 0:
                data_by_svc[svc][repl].append({
                    "p95": metrics["p95_ms"],
                    "cpu": metrics["cpu_pct"]
                })

print("="*60)
print("HPA SCALING EFFECTIVENESS ANALYSIS (Reactive Run)")
print("="*60)

for svc in ["front-end", "carts", "orders"]:
    print(f"\n--- Service: {svc.upper()} ---")
    print(f"{'Replicas':>8} | {'N (intervals)':>13} | {'Avg p95 (ms)':>12} | {'Max p95 (ms)':>12} | {'Avg CPU %':>10}")
    print("-" * 65)
    
    svc_data = data_by_svc[svc]
    for repl in sorted(svc_data.keys()):
        intervals = svc_data[repl]
        n = len(intervals)
        avg_p95 = sum(m["p95"] for m in intervals) / n
        max_p95 = max(m["p95"] for m in intervals)
        avg_cpu = sum(m["cpu"] for m in intervals) / n
        
        print(f"{repl:8d} | {n:13d} | {avg_p95:12.1f} | {max_p95:12.1f} | {avg_cpu:9.1f}%")

print("\n" + "="*60)
print("Load Pattern Context:")
print("- Step bursts hitting at specific intervals")
print("- When load spikes, CPU and p95 spike, triggering HPA to add replicas.")
print("="*60)
