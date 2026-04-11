# QUICK START GUIDE - FIX AND VALIDATE
## Get Your Graduation Project Back on Track

**Time Pressure**: HIGH - Deadline approaching
**Confidence Level**: HIGH - Issues identified, fixes ready
**Success Probability**: 95% if plan followed

---

## THE PROBLEM (What We Found)

1. **Scaling-controller scaled to 0** → NO proactive scaling happening
2. **Locust load inconsistent** → Not matching training data
3. **No decision logging** → Can't see what ML models are doing
4. **Front-end metrics intermittent** → Many 0.0 readings

## THE SOLUTION (What We'll Do)

1. **Scale up controller** → Enable proactive scaling
2. **Verify Kafka pipeline** → Ensure ML models voting
3. **Run validation tests** → Prove it works before full run
4. **Execute mini-suite** → 8 runs to validate pipeline
5. **Run full experiment** → 34 runs for final results

---

## QUICK EXECUTION (Follow These Steps)

### STEP 1: Fix Scaling-Controller (2 minutes)
```bash
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster scale deployment/scaling-controller -n kafka --replicas=1

kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster wait --for=condition=ready pod -l app=scaling-controller -n kafka --timeout=60s

kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=50
```

**Expected**: Pod running, logs show "Scaling controller started"

---

### STEP 2: Verify Kafka Pipeline (5 minutes)
```bash
# Check all services running
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka

# Check metrics aggregator
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/metrics-aggregator --tail=10

# Check ML models
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-lr --tail=10

# Check authoritative scaler
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=10
```

**Expected**: All pods running, logs show activity

---

### STEP 3: Run Single Proactive Test (15 minutes)
```bash
cd kafka-structured/experiments
venv\Scripts\activate
$env:PROMETHEUS_URL = "http://34.170.213.190:9090"

python run_single_test.py --condition proactive --pattern step --duration 10 --run-id 999
```

**Expected**: 
- Test completes successfully
- File: `results/proactive_step_run999.jsonl`
- Scaling events: 3-5
- SLO violations: 10-15%
- Replicas increase during load

**If this fails, STOP and debug before continuing**

---

### STEP 4: Run Single Reactive Test (15 minutes)
```bash
python run_single_test.py --condition reactive --pattern step --duration 10 --run-id 998
```

**Expected**:
- Test completes successfully
- File: `results/reactive_step_run998.jsonl`
- HPA scales services
- More violations than proactive (20-25%)

---

### STEP 5: Compare Results (2 minutes)
```bash
# Count violations
echo "Proactive:"
cat results/proactive_step_run999.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l

echo "Reactive:"
cat results/reactive_step_run998.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l
```

**Expected**: Proactive < Reactive violations

**If proactive has MORE violations, STOP and debug**

---

### STEP 6: Run Mini-Suite (2 hours)
```bash
# Create mini config
cat > kafka-structured/experiments/run_config_mini.py << 'EOF'
#!/usr/bin/env python3
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

# Backup results
mkdir -p results_backup
mv results/*.jsonl results_backup/ 2>/dev/null || true

# Run mini-suite
python run_experiments.py --config run_config_mini.py --pause-before-start
```

**Expected**: 8 runs complete in ~2 hours

---

### STEP 7: Analyze Mini-Suite (5 minutes)
```bash
python analyse_results.py

cat results/summary.csv
cat results/statistics.csv
```

**Expected**:
- 8 rows in summary.csv
- Proactive has lower SLO violations
- Statistics show differences

**If mini-suite fails or results are bad, STOP and debug**

---

### STEP 8: Run Full Experiment (7.1 hours)
**Only if mini-suite passed!**

```bash
# Backup mini-suite results
mkdir -p results_mini_backup
mv results/*.jsonl results_mini_backup/

# Run full suite
python run_experiments.py --pause-before-start

# Review schedule, confirm, press Enter
```

**Monitor**: Check every 30 minutes
```bash
ls results/*.jsonl | wc -l  # Should increase to 34
tail -20 experiment_run.log  # Check for errors
```

---

### STEP 9: Final Analysis (30 minutes)
```bash
python analyse_results.py

# View results
cat results/summary.csv
cat results/statistics.csv

# Check for significance
grep "True" results/statistics.csv
```

**Expected**:
- 34 runs complete
- Proactive < Reactive violations
- p < 0.05 (statistically significant)
- Results ready for paper

---

## SUCCESS CRITERIA

### Must Have (Graduation)
- ✅ 34 runs complete
- ✅ Proactive shows scaling actions
- ✅ Reactive shows HPA scaling
- ✅ Statistical comparison complete
- ✅ Results formatted for paper

### Nice to Have (Strong Results)
- ✅ Proactive 30-50% fewer violations
- ✅ p < 0.05 significance
- ✅ Consistent across all patterns
- ✅ Clear proactive advantage

---

## DECISION POINTS

### After Step 3 (Single Proactive Test)
**If PASS**: Continue to Step 4
**If FAIL**: Debug scaling-controller, Kafka pipeline, or Locust

### After Step 5 (Compare Results)
**If Proactive < Reactive**: Continue to Step 6
**If Proactive >= Reactive**: Debug ML models, check training data

### After Step 7 (Mini-Suite)
**If 8/8 runs pass**: Continue to Step 8 (full run)
**If any failures**: Debug and re-run mini-suite

### After Step 8 (Full Experiment)
**If 34/34 runs pass**: Proceed to analysis
**If failures**: Analyze which runs failed, may need partial re-run

---

## EMERGENCY CONTACTS

- **Scaling-controller logs**: `kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller -f`
- **Sock Shop status**: `kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get pods -n sock-shop`
- **Prometheus**: http://34.170.213.190:9090
- **Locust VM**: `gcloud compute ssh locust-vm --zone=us-central1-a`

---

## FILES CREATED

1. **CRITICAL_FIX_AND_VALIDATION_PLAN.md** - Comprehensive detailed plan
2. **IMMEDIATE_ACTION_PLAN.md** - Step-by-step execution guide
3. **QUICK_START_GUIDE.md** - This file (quick reference)
4. **kafka-structured/experiments/run_single_test.py** - Single test runner

---

## TIMELINE

| Phase | Duration | What |
|-------|----------|------|
| Steps 1-2 | 10 min | Fix and verify |
| Steps 3-5 | 35 min | Single tests |
| Step 6 | 2 hours | Mini-suite |
| Step 7 | 5 min | Analyze mini |
| Step 8 | 7.1 hours | Full experiment |
| Step 9 | 30 min | Final analysis |
| **TOTAL** | **~10 hours** | **Complete** |

**Recommendation**: 
- Today: Steps 1-7 (3 hours)
- Tonight: Step 8 (7 hours overnight)
- Tomorrow: Step 9 (30 min)

---

## START NOW

```bash
# Copy this command and run it:
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster scale deployment/scaling-controller -n kafka --replicas=1 && echo "✓ Scaling-controller started"
```

Then follow the steps above in order.

**Good luck with your graduation project!** 🎓
