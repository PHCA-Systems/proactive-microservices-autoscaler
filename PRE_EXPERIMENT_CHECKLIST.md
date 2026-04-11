# PRE-EXPERIMENT CHECKLIST
## Verify Everything Before Starting Full 34-Run Experiment

**Purpose**: Ensure system is ready for 7+ hour unattended experiment run
**When to Use**: After mini-suite passes, before starting full experiment
**Critical**: Do NOT skip any items

---

## INFRASTRUCTURE HEALTH

### GKE Clusters
- [ ] Sock-shop cluster accessible
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster cluster-info
  ```

- [ ] Pipeline cluster accessible
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster cluster-info
  ```

- [ ] All nodes Ready
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get nodes
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get nodes
  ```

### Sock Shop Services
- [ ] All 7 services running (1 replica each initially)
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get deployments -n sock-shop
  ```
  Expected: front-end, carts, orders, catalogue, user, payment, shipping (all 1/1)

- [ ] No pods in CrashLoopBackOff
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get pods -n sock-shop
  ```

- [ ] Front-end accessible
  ```bash
  curl -I http://104.154.246.88/
  ```
  Expected: HTTP 200

### Kafka Infrastructure
- [ ] Kafka broker running
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep kafka
  ```

- [ ] All topics exist
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster exec -n kafka kafka-0 -- kafka-topics.sh --bootstrap-server localhost:9092 --list
  ```
  Expected: metrics, model-votes, scaling-decisions

- [ ] Metrics-aggregator running and publishing
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/metrics-aggregator --tail=5
  ```
  Expected: Recent log entries (within last 30s)

- [ ] All 3 ML inference services running
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep ml-inference
  ```
  Expected: ml-inference-lr, ml-inference-rf, ml-inference-xgb (all Running)

- [ ] Authoritative-scaler running
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep authoritative
  ```

- [ ] Scaling-controller running (for proactive tests)
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka | grep scaling-controller
  ```
  Expected: 1/1 Running

### Monitoring
- [ ] Prometheus accessible
  ```bash
  curl -s http://34.170.213.190:9090/api/v1/status/config | jq .status
  ```
  Expected: "success"

- [ ] Prometheus has recent data
  ```bash
  curl -s "http://34.170.213.190:9090/api/v1/query?query=up" | jq '.data.result | length'
  ```
  Expected: > 0

### Load Generator
- [ ] Locust VM accessible
  ```bash
  gcloud compute ssh locust-vm --zone=us-central1-a --command="echo 'VM accessible'"
  ```

- [ ] Locust can reach Sock Shop
  ```bash
  gcloud compute ssh locust-vm --zone=us-central1-a --command="curl -I http://104.154.246.88/"
  ```
  Expected: HTTP 200

---

## EXPERIMENT CONFIGURATION

### Python Environment
- [ ] Virtual environment activated
  ```bash
  # Windows
  venv\Scripts\activate
  
  # Linux/Mac
  source venv/bin/activate
  ```

- [ ] Required packages installed
  ```bash
  pip list | grep -E "(requests|kubernetes|scipy|numpy)"
  ```
  Expected: All packages present

- [ ] Prometheus URL set
  ```bash
  # Windows
  echo $env:PROMETHEUS_URL
  
  # Linux/Mac
  echo $PROMETHEUS_URL
  ```
  Expected: http://34.170.213.190:9090

### Configuration Files
- [ ] run_config.py has correct settings
  ```bash
  cat kafka-structured/experiments/run_config.py | grep -E "(SLO_THRESHOLD|REPETITIONS)"
  ```
  Expected:
  - SLO_THRESHOLD_MS = 36.0
  - constant: 2, step: 5, spike: 5, ramp: 5

- [ ] run_experiments.py exists and is executable
  ```bash
  ls -l kafka-structured/experiments/run_experiments.py
  ```

- [ ] analyse_results.py exists
  ```bash
  ls -l kafka-structured/experiments/analyse_results.py
  ```

### Results Directory
- [ ] Results directory exists
  ```bash
  ls -ld results/
  ```

- [ ] Results directory is empty or backed up
  ```bash
  ls results/*.jsonl 2>/dev/null | wc -l
  ```
  Expected: 0 (or files backed up)

- [ ] Sufficient disk space (at least 1GB free)
  ```bash
  df -h | grep -E '(Filesystem|/$)'
  ```

---

## VALIDATION TESTS PASSED

### Single Test Results
- [ ] Proactive test completed successfully
  - File: results/proactive_step_run999.jsonl exists
  - Has 20 snapshots
  - Shows scaling actions (replicas > 1)
  - SLO violations: 10-15%

- [ ] Reactive test completed successfully
  - File: results/reactive_step_run998.jsonl exists
  - Has 20 snapshots
  - Shows HPA scaling
  - SLO violations: 20-30%

- [ ] Proactive < Reactive violations
  ```bash
  echo "Proactive violations:"
  cat results/proactive_step_run999.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l
  
  echo "Reactive violations:"
  cat results/reactive_step_run998.jsonl | jq -r 'select(.services["front-end"].slo_violated == true)' | wc -l
  ```

### Mini-Suite Results
- [ ] All 8 runs completed
  ```bash
  ls results_mini_backup/*.jsonl | wc -l
  ```
  Expected: 8

- [ ] Analysis shows proactive advantage
  ```bash
  cat results_mini_backup/statistics.csv | grep slo_violation_rate
  ```
  Expected: Proactive mean < Reactive mean

- [ ] No errors in experiment log
  ```bash
  grep -i error experiment_run.log | wc -l
  ```
  Expected: 0 or only minor warnings

---

## SYSTEM BEHAVIOR VERIFICATION

### Proactive Condition
- [ ] Scaling-controller receives decisions
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=20 | grep -i decision
  ```

- [ ] ML models vote with confidence
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=20 | grep -i vote
  ```

- [ ] Scaling actions occur
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/scaling-controller --tail=20 | grep -i scaling
  ```

- [ ] HPA is NOT applied
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get hpa -n sock-shop
  ```
  Expected: No resources found (or error)

### Reactive Condition
- [ ] HPA applied to all 7 services
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get hpa -n sock-shop | wc -l
  ```
  Expected: 8 (7 services + header)

- [ ] Scaling-controller scaled to 0
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get deployment -n kafka scaling-controller -o jsonpath='{.spec.replicas}'
  ```
  Expected: 0

- [ ] HPA scales based on CPU
  ```bash
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get hpa -n sock-shop
  ```
  Expected: Shows CPU targets (70%)

### Load Generation
- [ ] Constant pattern generates steady load
  - Request rate: ~0.65 req/s
  - p95 latency: ~4.75ms

- [ ] Step pattern generates increasing load
  - Request rate: 14→47 req/s
  - p95 latency: increases to 63-173ms

- [ ] Spike pattern generates bursts
  - Request rate: spikes to 100 users
  - p95 latency: spikes > 100ms

- [ ] Ramp pattern generates gradual increase
  - Request rate: gradual increase
  - p95 latency: gradual increase

### Metrics Collection
- [ ] All 7 services monitored
  ```bash
  tail -1 results/proactive_step_run999.jsonl | jq '.services | keys'
  ```
  Expected: ["carts", "catalogue", "front-end", "orders", "payment", "shipping", "user"]

- [ ] Replica counts accurate
  - Compare JSONL with kubectl output
  - Should match exactly

- [ ] p95 latency reasonable
  - Baseline: 4.75ms
  - Under load: 63-714ms
  - Matches training data ranges

- [ ] CPU usage reasonable
  - Idle: 0.2-2%
  - Under load: 5-20%
  - Matches training data

---

## MONITORING SETUP

### Dashboards
- [ ] Grafana accessible (if using)
  ```bash
  # Check if Grafana is running
  kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get svc -n sock-shop | grep grafana
  ```

- [ ] Prometheus dashboard open in browser
  - URL: http://34.170.213.190:9090

### Logging
- [ ] Experiment log file writable
  ```bash
  touch experiment_run.log && echo "test" >> experiment_run.log
  ```

- [ ] Log monitoring script ready
  ```bash
  cat > monitor_experiments.sh << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== Experiment Progress ==="
    echo "Completed: $(ls results/*.jsonl 2>/dev/null | wc -l) / 34"
    echo ""
    echo "=== Latest Log ==="
    tail -5 experiment_run.log
    echo ""
    echo "=== Service Health ==="
    kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get pods -n sock-shop | grep -v Running || echo "All running"
    echo ""
    sleep 300
done
EOF
  chmod +x monitor_experiments.sh
  ```

### Alerts
- [ ] Phone/laptop charged (for monitoring)
- [ ] Notifications enabled (if using)
- [ ] Backup plan if experiment fails

---

## TIME AND RESOURCES

### Time Availability
- [ ] 7+ hours available for unattended run
- [ ] Can check progress every 2-3 hours
- [ ] Morning available for analysis

### Resource Limits
- [ ] GKE quota sufficient
  ```bash
  gcloud compute project-info describe --project=grad-phca | grep -A 5 quotas
  ```

- [ ] No scheduled maintenance
  ```bash
  gcloud compute operations list --filter="status:RUNNING" --project=grad-phca
  ```

- [ ] Billing account active
  ```bash
  gcloud beta billing accounts list
  ```

---

## BACKUP AND RECOVERY

### Backups
- [ ] Previous results backed up
  ```bash
  ls -lh results_backup/ results_mini_backup/
  ```

- [ ] Configuration files backed up
  ```bash
  cp kafka-structured/experiments/run_config.py kafka-structured/experiments/run_config.py.backup
  ```

### Recovery Plan
- [ ] Know how to stop experiment
  ```bash
  # Ctrl+C or kill process
  ps aux | grep run_experiments.py
  ```

- [ ] Know how to restart from failure
  - Identify which run failed
  - Delete incomplete JSONL file
  - Restart from that run

- [ ] Know how to scale down resources
  ```bash
  # Reset all services to 1 replica
  for svc in front-end carts orders catalogue user payment shipping; do
    kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster scale deployment/$svc -n sock-shop --replicas=1
  done
  ```

---

## FINAL GO/NO-GO DECISION

### GO Criteria (All must be YES)
- [ ] All infrastructure health checks passed
- [ ] All validation tests passed
- [ ] Mini-suite showed proactive advantage
- [ ] 7+ hours available
- [ ] Monitoring setup complete
- [ ] Backups complete
- [ ] Confident in system stability

### NO-GO Criteria (Any is STOP)
- [ ] Any infrastructure failures
- [ ] Validation tests failed
- [ ] Mini-suite showed no advantage
- [ ] Insufficient time available
- [ ] System instability
- [ ] Unresolved errors

---

## EXECUTION COMMAND

If all checks passed:

```bash
cd kafka-structured/experiments
source venv/bin/activate  # or venv\Scripts\activate on Windows
export PROMETHEUS_URL="http://34.170.213.190:9090"  # or $env:PROMETHEUS_URL on Windows

# Final confirmation
echo "Starting full 34-run experiment in 10 seconds..."
echo "Press Ctrl+C to abort"
sleep 10

# Start experiment
python run_experiments.py --pause-before-start

# Review schedule
# Confirm to start
# Press Enter

# Start monitoring (separate terminal)
./monitor_experiments.sh
```

---

## POST-EXPERIMENT VERIFICATION

After completion:

- [ ] All 34 JSONL files exist
  ```bash
  ls results/*.jsonl | wc -l
  ```

- [ ] Each file has 20 snapshots
  ```bash
  for f in results/*.jsonl; do echo "$f: $(wc -l < $f)"; done | grep -v " 20$"
  ```
  Expected: No output (all have 20 lines)

- [ ] No errors in log
  ```bash
  grep -i error experiment_run.log
  ```

- [ ] Analysis runs successfully
  ```bash
  python analyse_results.py
  ```

- [ ] Results show proactive advantage
  ```bash
  cat results/statistics.csv | grep slo_violation_rate
  ```

---

## CHECKLIST SUMMARY

Total items: ~80
Required for GO: 100% of GO criteria
Time to complete: 30-45 minutes

**Print this checklist and check off items as you verify them.**

**Do NOT start full experiment until ALL items are checked!**
