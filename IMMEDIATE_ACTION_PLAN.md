# IMMEDIATE ACTION PLAN
## Fix and Validate Before Final Experiments

**Current Time**: Ready to start
**Estimated Completion**: 3-4 hours for all fixes + validation
**Critical Path**: Fix → Test → Validate → Mini-Suite → Full Run

---

## STEP 1: FIX SCALING-CONTROLLER (5 minutes)

### Issue
Scaling-controller deployment exists but scaled to 0 replicas
- This is why NO proactive scaling happened
- Deployment shows: `0/0` replicas

### Fix
```bash
# Scale up the controller
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster scale deployment/scaling-controller -n kafka --replicas=1

# Wait for pod to be ready
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster wait --for=condition=ready pod -l app=scaling-controller -n kafka --timeout=60s

# Check pod status
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep scaling

# Check logs
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=50
```

### Expected Output
```
scaling-controller-xxxxx   1/1     Running   0          30s
```

Logs should show:
- "Scaling controller started"
- "Connected to Kafka"
- "Subscribed to scaling-decisions topic"
- NO 403 Forbidden errors

---

## STEP 2: VERIFY KAFKA PIPELINE (10 minutes)

### Check All Services Running
```bash
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka
```

Expected: All pods Running (1/1)
- kafka-0
- metrics-aggregator-xxxxx
- ml-inference-lr-xxxxx
- ml-inference-rf-xxxxx
- ml-inference-xgb-xxxxx
- authoritative-scaler-xxxxx
- scaling-controller-xxxxx

### Verify Kafka Topics
```bash
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster exec -n kafka kafka-0 -- kafka-topics.sh --bootstrap-server localhost:9092 --list
```

Expected topics:
- metrics
- model-votes
- scaling-decisions

### Check Metrics Flow
```bash
# Metrics aggregator publishing
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/metrics-aggregator --tail=20

# ML services consuming and voting
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-lr --tail=10
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-rf --tail=10
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-xgb --tail=10

# Authoritative scaler aggregating
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=20

# Scaling controller receiving decisions
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=20
```

### Sample Kafka Messages
```bash
# Check model votes (should see 3 models voting)
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster exec -n kafka kafka-0 -- kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic model-votes --max-messages 10 --timeout-ms 10000

# Check scaling decisions
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster exec -n kafka kafka-0 -- kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic scaling-decisions --max-messages 5 --timeout-ms 10000
```

---

## STEP 3: VERIFY LOCUST LOAD GENERATION (10 minutes)

### Check Locust VM
```bash
# SSH to Locust VM
gcloud compute ssh locust-vm --zone=us-central1-a

# Check if Locust is running
ps aux | grep locust

# Check Locust stats
curl http://localhost:8089/stats/requests | jq .

# Verify Sock Shop reachable
curl -I http://104.154.246.88/

# Exit VM
exit
```

### Test Load Pattern
```bash
# From local machine, trigger a test load
# (This will be done by run_single_test.py)
```

---

## STEP 4: RUN SINGLE PROACTIVE TEST (15 minutes)

### Purpose
Verify proactive autoscaling works end-to-end with scaling actions

### Execute
```bash
cd kafka-structured/experiments

# Activate venv (Windows)
venv\Scripts\activate

# Set Prometheus URL
$env:PROMETHEUS_URL = "http://34.170.213.190:9090"

# Run single test
python run_single_test.py --condition proactive --pattern step --duration 10 --run-id 999
```

### Monitor During Test
```bash
# In separate terminal, watch scaling controller logs
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller -f

# Watch replica counts
watch -n 5 'kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get deployments -n sock-shop -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas'
```

### Success Criteria
✅ Test completes without errors
✅ Output file: `results/proactive_step_run999.jsonl`
✅ File has 20 snapshots
✅ Replica counts CHANGE during test (not all 1)
✅ Scaling events logged (at least 2-3)
✅ SLO violations detected (5-15%)
✅ Scaling happens BEFORE or DURING violations

### Expected Behavior
- Intervals 0-8: Low load, replicas=1, p95~4.75ms
- Intervals 9-10: Load increases, p95>36ms
- Intervals 8-10: ML models predict, vote SCALE_UP
- Intervals 10-15: Replicas increase (2-3), p95 improves
- Scaling events: 3-5 total

### If Test Fails
Check:
1. Scaling-controller logs for errors
2. ML model votes in Kafka (are they voting SCALE_UP?)
3. Authoritative-scaler consensus (is it deciding SCALE_UP?)
4. Kubernetes RBAC (can controller scale deployments?)
5. Locust load (is traffic actually being generated?)

---

## STEP 5: RUN SINGLE REACTIVE TEST (15 minutes)

### Purpose
Verify reactive HPA baseline works correctly

### Execute
```bash
# Run reactive test
python run_single_test.py --condition reactive --pattern step --duration 10 --run-id 998
```

### Monitor During Test
```bash
# Watch HPA status
watch -n 5 'kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get hpa -n sock-shop'

# Watch replica counts
watch -n 5 'kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get deployments -n sock-shop -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas'
```

### Success Criteria
✅ Test completes without errors
✅ Output file: `results/reactive_step_run998.jsonl`
✅ HPA applied to all 7 services
✅ Scaling-controller scaled to 0 (not running)
✅ Replica counts CHANGE when CPU > 70%
✅ Scaling happens AFTER violations (reactive delay)
✅ More violations than proactive test

### Expected Behavior
- Intervals 0-9: Low load, replicas=1, CPU<70%
- Interval 10: Load spike, CPU>70%, p95>36ms, SLO violated
- Interval 11-12: HPA scales up (1→2 or more)
- Intervals 13-15: CPU drops, p95 improves
- More SLO violations than proactive (15-25% vs 5-15%)

---

## STEP 6: COMPARE PROACTIVE VS REACTIVE (5 minutes)

### Analyze Both Tests
```bash
# Check proactive results
cat results/proactive_step_run999.jsonl | jq -r '.services["front-end"] | "\(.replicas) replicas, \(.p95_ms)ms p95, violated=\(.slo_violated)"'

# Check reactive results
cat results/reactive_step_run998.jsonl | jq -r '.services["front-end"] | "\(.replicas) replicas, \(.p95_ms)ms p95, violated=\(.slo_violated)"'

# Count violations
echo "Proactive violations:"
cat results/proactive_step_run999.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l

echo "Reactive violations:"
cat results/reactive_step_run998.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l

# Count scaling events
echo "Proactive scaling events:"
cat results/proactive_step_run999.jsonl | jq -r '.services | to_entries[] | "\(.key): \(.value.replicas)"' | sort | uniq -c

echo "Reactive scaling events:"
cat results/reactive_step_run998.jsonl | jq -r '.services | to_entries[] | "\(.key): \(.value.replicas)"' | sort | uniq -c
```

### Expected Comparison
| Metric | Proactive | Reactive | Winner |
|--------|-----------|----------|--------|
| SLO Violations | 2-3 (10-15%) | 4-5 (20-25%) | Proactive ✓ |
| Scaling Events | 3-5 | 2-4 | Proactive ✓ |
| Max Replicas | 2-3 | 3-5 | Proactive ✓ |
| Scaling Timing | Before/During | After | Proactive ✓ |

---

## STEP 7: RUN MINI-SUITE VALIDATION (2 hours)

### Purpose
Test full experiment pipeline with 8 runs before committing to 34 runs

### Configuration
Create mini config:
```bash
cat > kafka-structured/experiments/run_config_mini.py << 'EOF'
#!/usr/bin/env python3
"""Mini experiment configuration for validation"""

from dataclasses import dataclass

SLO_THRESHOLD_MS = 36.0
NAMESPACE = "sock-shop"
POLL_INTERVAL_S = 30

MONITORED_SERVICES = [
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

@dataclass
class ExperimentRun:
    condition: str
    pattern: str
    run_id: int

# Mini-suite: 1 of each pattern per condition = 8 runs
REPETITIONS = {
    "constant": 1,
    "step": 1,
    "spike": 1,
    "ramp": 1,
}

def generate_run_schedule() -> list[ExperimentRun]:
    schedule = []
    for pattern, reps in REPETITIONS.items():
        for i in range(1, reps + 1):
            schedule.append(ExperimentRun("proactive", pattern, i))
            schedule.append(ExperimentRun("reactive", pattern, i))
    return schedule
EOF
```

### Execute Mini-Suite
```bash
# Backup current results
mkdir -p results_backup
mv results/*.jsonl results_backup/ 2>/dev/null || true

# Run mini-suite
python run_experiments.py --config run_config_mini.py --pause-before-start
```

### Monitor Progress
```bash
# Watch file count
watch -n 60 'ls results/*.jsonl | wc -l'

# Check latest log
tail -f experiment_run.log
```

### Success Criteria
✅ All 8 runs complete (2 hours)
✅ 8 JSONL files in results/
✅ Each file has 20 snapshots
✅ No errors in experiment_run.log
✅ Proactive runs show scaling (replicas > 1)
✅ Reactive runs show HPA scaling
✅ Services don't crash
✅ Locust generates consistent load

### Analyze Mini-Suite
```bash
# Run analyzer
python analyse_results.py

# Check outputs
cat results/summary.csv
cat results/statistics.csv

# Verify columns present
head -1 results/summary.csv
# Expected: condition,pattern,run_id,slo_violation_rate,total_replica_seconds,avg_replicas,max_replicas,scaling_events,n_intervals

head -1 results/statistics.csv
# Expected: pattern,metric,proactive_mean,proactive_std,reactive_mean,reactive_std,p_value,significant
```

### Expected Mini-Suite Results
| Pattern | Metric | Proactive | Reactive | Better |
|---------|--------|-----------|----------|--------|
| constant | SLO violations | 0% | 0% | Tie |
| step | SLO violations | 10-15% | 20-30% | Proactive |
| spike | SLO violations | 15-25% | 30-40% | Proactive |
| ramp | SLO violations | 5-10% | 10-20% | Proactive |

---

## STEP 8: DECISION POINT

### If Mini-Suite PASSES
✅ Proceed to full 34-run experiment
✅ Estimated time: 7.1 hours
✅ Schedule overnight run
✅ Set up monitoring alerts

### If Mini-Suite FAILS
❌ Debug issues before full run
❌ Check which runs failed
❌ Review logs for errors
❌ Fix and re-run mini-suite

---

## STEP 9: FULL EXPERIMENT (7.1 hours)

### Only proceed if Step 7 (mini-suite) passed

### Pre-Flight Checklist
- [ ] Mini-suite completed successfully (8/8 runs)
- [ ] Analysis shows proactive < reactive violations
- [ ] All services healthy
- [ ] Kafka pipeline working
- [ ] Scaling-controller running
- [ ] Locust VM accessible
- [ ] Results directory backed up and cleared
- [ ] 7+ hours available uninterrupted
- [ ] Monitoring dashboard open

### Execute Full Suite
```bash
# Clear results
mkdir -p results_full_backup
mv results/*.jsonl results_full_backup/

# Run full 34-run suite
python run_experiments.py --pause-before-start

# Review schedule
# Confirm to start
# Press Enter
```

### Monitoring Script
```bash
# Create monitoring script
cat > monitor_experiments.sh << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== Experiment Progress ==="
    echo "Completed runs: $(ls results/*.jsonl 2>/dev/null | wc -l) / 34"
    echo ""
    echo "=== Latest Run ==="
    tail -5 experiment_run.log
    echo ""
    echo "=== Service Health ==="
    kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get pods -n sock-shop | grep -v Running || echo "All pods running"
    echo ""
    echo "=== Disk Space ==="
    df -h | grep -E '(Filesystem|/$)'
    echo ""
    echo "=== Next check in 5 minutes ==="
    sleep 300
done
EOF

chmod +x monitor_experiments.sh
./monitor_experiments.sh
```

### Abort Conditions
Stop and debug if:
- 3+ consecutive runs fail
- Services crash repeatedly
- Disk space < 10%
- Scaling-controller crashes
- Locust stops working

---

## STEP 10: FINAL ANALYSIS

### Generate Results
```bash
python analyse_results.py
```

### Validate Outputs
```bash
# Check all files present
ls results/*.jsonl | wc -l  # Should be 34

# Check summary
wc -l results/summary.csv  # Should be 35 (34 + header)

# Check statistics
cat results/statistics.csv

# View formatted table
python analyse_results.py | tail -50
```

### Key Questions to Answer
1. Does proactive have fewer SLO violations? (YES expected)
2. Is the difference statistically significant? (p < 0.05 expected)
3. Does proactive use similar resources? (Similar expected)
4. Does proactive scale preemptively? (YES expected)
5. Are results consistent across patterns? (YES expected)

---

## TROUBLESHOOTING GUIDE

### Issue: Scaling-controller not scaling
**Check**:
1. Pod running? `kubectl get pods -n kafka`
2. Logs show decisions? `kubectl logs -n kafka deployment/scaling-controller`
3. RBAC permissions? `kubectl auth can-i update deployments --as=system:serviceaccount:kafka:scaling-controller -n sock-shop`
4. Kafka connected? Check logs for "Connected to Kafka"

### Issue: No ML model votes
**Check**:
1. ML pods running? `kubectl get pods -n kafka | grep ml-inference`
2. Models loaded? Check logs for "Model loaded"
3. Metrics received? Check logs for "Received metrics"
4. Kafka connected? Check logs for "Connected to Kafka"

### Issue: Locust not generating load
**Check**:
1. Locust process running? `ps aux | grep locust` on VM
2. Sock Shop reachable? `curl http://104.154.246.88/`
3. Load pattern correct? Check Locust stats
4. SSH working? Test SSH to VM

### Issue: Metrics all 0.0
**Check**:
1. Prometheus accessible? `curl http://34.170.213.190:9090`
2. Query correct? Test query directly
3. Services have traffic? Check Locust stats
4. Metrics-aggregator working? Check logs

---

## TIMELINE SUMMARY

| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Fix scaling-controller | 5 min | 5 min |
| 2. Verify Kafka pipeline | 10 min | 15 min |
| 3. Verify Locust | 10 min | 25 min |
| 4. Single proactive test | 15 min | 40 min |
| 5. Single reactive test | 15 min | 55 min |
| 6. Compare results | 5 min | 60 min |
| 7. Mini-suite (8 runs) | 2 hours | 3 hours |
| 8. Decision point | 5 min | 3h 5min |
| 9. Full suite (34 runs) | 7.1 hours | 10h 8min |
| 10. Final analysis | 30 min | 10h 38min |

**Total**: ~11 hours (3 hours validation + 7 hours experiments + 1 hour analysis)

---

## NEXT IMMEDIATE ACTION

**START HERE**:
```bash
# Step 1: Scale up scaling-controller
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster scale deployment/scaling-controller -n kafka --replicas=1

# Wait and check
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster wait --for=condition=ready pod -l app=scaling-controller -n kafka --timeout=60s

# View logs
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=50
```

**Then proceed to Step 2**
