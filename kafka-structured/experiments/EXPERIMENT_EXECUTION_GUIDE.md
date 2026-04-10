# Experiment Execution Guide

## Overview

This guide explains how to execute the full 34-run experiment suite for the proactive autoscaler evaluation.

**Duration:** ~8.5 hours  
**Cost:** ~$4.60  
**Runs:** 34 (17 proactive + 17 reactive)

---

## Prerequisites Checklist

Before starting, verify all prerequisites are met:

- [ ] GKE clusters running (sock-shop-cluster, pipeline-cluster)
- [ ] All pipeline services running in kafka namespace
- [ ] All Sock Shop services running at 1 replica
- [ ] Locust VM running (IP: 35.222.116.125)
- [ ] Prometheus accessible (http://34.170.213.190:9090)
- [ ] kubectl configured with both cluster contexts
- [ ] SSH key available (~/.ssh/google_compute_engine)
- [ ] Python virtual environment set up
- [ ] Results directory empty or backed up

---

## Execution Methods

### Method 1: Using PowerShell Script (Recommended for Windows)

```powershell
cd kafka-structured/experiments
.\run_full_experiments.ps1
```

### Method 2: Using Bash Script (Linux/Mac)

```bash
cd kafka-structured/experiments
chmod +x run_full_experiments.sh
./run_full_experiments.sh
```

### Method 3: Manual Execution

```powershell
# 1. Activate virtual environment
kafka-structured\services\metrics-aggregator\venv\Scripts\Activate.ps1

# 2. Set environment variables
$env:PROMETHEUS_URL = "http://34.170.213.190:9090"
$env:LOCUST_VM_IP = "35.222.116.125"
$env:LOCUST_SSH_USER = "User"
$env:LOCUST_SSH_KEY = "$HOME/.ssh/google_compute_engine"
$env:SOCK_SHOP_EXTERNAL_IP = "104.154.246.88"

# 3. Switch to sock-shop cluster context
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster

# 4. Run experiments
cd kafka-structured/experiments
python run_experiments.py --pause-before-start
```

---

## What Happens During Execution

### Phase 1: Validation (1-2 minutes)
- Checks all 7 service deployments exist
- Verifies scaling controller deployment
- Tests Prometheus connectivity
- Tests Locust VM SSH access

### Phase 2: Schedule Display
- Shows the 34-run schedule
- Displays estimated time and cost
- Waits for user confirmation (press ENTER)

### Phase 3: Experiment Execution (~8.5 hours)
For each of the 34 runs:
1. **Condition Setup** (15-30 seconds)
   - Switches to proactive or reactive mode
   - Resets all services to 1 replica
   - Waits for stabilization

2. **Load Generation** (12 minutes)
   - Starts Locust on remote VM
   - Generates load using specified pattern
   - Collects metrics every 30 seconds (24 snapshots)

3. **Settling Period** (3 minutes)
   - Stops load generator
   - Allows system to stabilize
   - Saves results to JSONL file

### Phase 4: Completion
- Reports success/failure for each run
- Saves all results to `experiments/results/` directory

---

## Monitoring Progress

### Check Experiment Progress
```powershell
# Count completed runs
Get-ChildItem kafka-structured/experiments/results/*.jsonl | Measure-Object
```

### Monitor Live Logs
```powershell
# Watch experiment runner output
# (The script will show live progress)
```

### Check Service Health
```powershell
# Pipeline services
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka

# Sock Shop services
kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get deployments -n sock-shop
```

### Check Scaling Controller Logs
```powershell
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka -l app=scaling-controller --tail=50
```

---

## Expected Output Files

After completion, you should have 34 JSONL files in `experiments/results/`:

```
proactive_constant_run01.jsonl
reactive_constant_run01.jsonl
proactive_constant_run02.jsonl
reactive_constant_run02.jsonl
proactive_step_run01.jsonl
reactive_step_run01.jsonl
...
proactive_ramp_run05.jsonl
reactive_ramp_run05.jsonl
```

Each file contains 24 snapshots (one per 30-second interval during the 12-minute load period).

---

## Troubleshooting

### Issue: Locust VM Connection Timeout
**Solution:**
```powershell
# Check VM status
gcloud compute instances list --filter="name=locust-runner"

# Start VM if stopped
gcloud compute instances start locust-runner --zone=us-central1-a

# Get new IP
gcloud compute instances describe locust-runner --zone=us-central1-a --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

# Update environment variable
$env:LOCUST_VM_IP = "<new_ip>"
```

### Issue: Prometheus Not Accessible
**Solution:**
```powershell
# Test connectivity
curl http://34.170.213.190:9090/api/v1/query?query=up

# If fails, use port-forward
kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster port-forward -n monitoring svc/prometheus-server 9090:80
$env:PROMETHEUS_URL = "http://localhost:9090"
```

### Issue: Scaling Controller Not Starting
**Solution:**
```powershell
# Check deployment
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get deployment scaling-controller -n kafka

# Check logs
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka -l app=scaling-controller

# Restart if needed
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster rollout restart deployment/scaling-controller -n kafka
```

### Issue: Experiment Interrupted
**Solution:**
- Results are saved after each run completes
- You can resume by manually editing the schedule in run_experiments.py
- Or re-run only the missing patterns

---

## After Experiments Complete

### 1. Analyze Results
```powershell
cd kafka-structured/experiments
python analyse_results.py
```

This will generate:
- `summary.csv` - Per-run metrics
- `statistics.csv` - Statistical comparison results
- Console output with formatted tables

### 2. Review Results
- Check `summary.csv` for per-run SLO violations and resource usage
- Check `statistics.csv` for Mann-Whitney U test results
- Look for p-values < 0.05 (statistically significant differences)

### 3. Clean Up (Optional)
```powershell
# Stop Locust VM to save costs
gcloud compute instances stop locust-runner --zone=us-central1-a

# Scale down pipeline services
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster scale deployment --all -n kafka --replicas=0

# Or delete clusters entirely
gcloud container clusters delete sock-shop-cluster --zone=us-central1-a
gcloud container clusters delete pipeline-cluster --zone=us-central1-a
```

---

## Cost Management

### Hourly Costs
- sock-shop-cluster: $0.40/hr
- pipeline-cluster: $0.13/hr
- Locust VM: ~$0.01/hr
- **Total:** ~$0.54/hr

### Experiment Cost
- 8.5 hours × $0.54/hr = **~$4.60**

### Cost Optimization
- Stop Locust VM when not in use
- Scale down pipeline services between experiments
- Delete clusters after experiments complete

---

## Notes

- The experiment runner uses `--pause-before-start` flag to show the schedule and wait for confirmation
- Each run is independent - if one fails, others continue
- Results are saved immediately after each run completes
- The system automatically switches between proactive and reactive conditions
- All services are reset to 1 replica before each run

---

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review system logs (kubectl logs)
3. Verify all prerequisites are met
4. Check the SYSTEM_READINESS_VALIDATION.md document

---

**Ready to run experiments!**
