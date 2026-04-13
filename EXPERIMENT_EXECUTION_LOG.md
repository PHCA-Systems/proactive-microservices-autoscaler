# Experiment Execution Log

## Launch Information
- **Start Time:** 2026-04-13 05:49:55
- **Total Runs:** 34
- **Estimated Duration:** 5.7 hours
- **Estimated Completion:** 2026-04-13 11:29:49
- **Log File:** `d:\Projects\Grad\PHCA\kafka-structured\experiments\experiment_run_log.txt`

## Infrastructure Validated
✅ Kubernetes cluster: `gke_grad-phca_us-central1-a_sock-shop-cluster`  
✅ Prometheus: `http://34.170.213.190:9090`  
✅ Locust VM: `35.222.116.125`  
✅ Sock Shop IP: `104.154.246.88`  
✅ SLO: `35.68ms` p95 latency

## Experiment Schedule
1. proactive constant run1 → reactive constant run1
2. proactive constant run2 → reactive constant run2
3. proactive step run1-5 → reactive step run1-5 (10 runs)
4. proactive spike run1-5 → reactive spike run1-5 (10 runs)
5. proactive ramp run1-5 → reactive ramp run1-5 (10 runs)

## Progress Checkpoints
- **05:49:55** - Run 1/34 started (proactive_constant_run01)
- **05:52:00** - Load test active, collecting 12 snapshots

## Monitoring Schedule
Will check every 30 minutes for:
- Current run number
- Any errors or failures
- Result file creation
- Completion status

## Post-Completion Tasks
1. ✅ Verify 34 .jsonl files exist
2. ✅ Run full_analysis.py
3. ✅ Create EXPERIMENT_RESULTS_SUMMARY.md
4. ✅ Push to GitHub
5. ✅ Send completion email

---
*This log will be updated periodically during execution*
