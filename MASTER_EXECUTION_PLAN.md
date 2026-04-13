# MASTER EXECUTION PLAN — Full 34-Run Experiment Suite

> **CRITICAL: This is a graduation-grade overnight run. There are NO do-overs.**

---

## Context

Proactive ML-based Microservices Autoscaler (PHCA) graduation project. All bugs fixed (see `phca_problems_summary.md`). System validated: Proactive achieves 7.9% SLO violations vs HPA's 45.0% while using 72.6% fewer resources.

### Infrastructure
- **Target Cluster:** `gke_grad-phca_us-central1-a_sock-shop-cluster`
- **Pipeline Cluster:** `gke_grad-phca_us-central1-a_pipeline-cluster`
- **Prometheus:** `http://34.170.213.190:9090`
- **Locust VM:** `35.222.116.125` (SSH user: `User`, key: `~/.ssh/google_compute_engine`)
- **Sock Shop IP:** `104.154.246.88`
- **SLO:** `35.68ms` p95 latency

---

## LAUNCH COMMAND

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments
python -u run_experiments.py 2>&1 | Tee-Object -FilePath "experiment_run_log.txt"
```

**No `--pause-before-start` flag.** The script launches immediately after validation.

**Estimated runtime:** ~7 hours (34 runs x ~12 min each)

---

## POST-EXPERIMENT: Verify & Analyze

### 1. Verify all 34 files exist

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments\results
Get-ChildItem *.jsonl | Where-Object { $_.Name -notlike "diag_*" } | Measure-Object
# Expected: Count = 34
```

### 2. Run analysis

```powershell
cd d:\Projects\Grad\PHCA
python -u full_analysis.py | Tee-Object -FilePath "experiment_analysis_output.txt"
```

### 3. Create EXPERIMENT_RESULTS_SUMMARY.md from the analysis output

### 4. Push to GitHub

```powershell
cd d:\Projects\Grad\PHCA
git add -A
git commit -m "Final experiment results: 34-run suite complete with analysis"
git push origin main
```

### 5. Send email to ahmedd.eldarawi@gmail.com saying "Congrats! Results are ready."

---

## PROMPT FOR NEXT AI SESSION

Copy-paste everything below this line into a new AI chat:

---

I need you to execute my graduation project's final experiment pipeline. Everything is at `d:\Projects\Grad\PHCA`. Here is exactly what to do:

**STEP 1: Launch the 34-run experiment suite**

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments
python -u run_experiments.py 2>&1 | Tee-Object -FilePath "experiment_run_log.txt"
```

This will take approximately 7 hours. The script:
- Validates infrastructure (Prometheus, Locust VM, Kubernetes)
- Auto-starts immediately (no pause/input needed)
- Runs 34 experiments: 4 load patterns x 2 conditions (proactive vs reactive) x multiple reps
- Prints a rich progress dashboard showing: run #, condition, pattern, per-interval metrics table, violation counts, timestamps, ETAs
- Saves each run as a `.jsonl` file in `kafka-structured/experiments/results/`
- Continues past errors (won't crash the whole suite if one run fails)

**Your job while it runs:** Monitor the log file periodically. Do NOT try to interact with stdin. Just check progress with:
```powershell
Get-Content "d:\Projects\Grad\PHCA\kafka-structured\experiments\experiment_run_log.txt" -Tail 20
```

**STEP 2: After experiments finish, verify results**

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments\results
Get-ChildItem *.jsonl | Where-Object { $_.Name -notlike "diag_*" } | Measure-Object
```
Expected count: 34. If any are missing, note which ones failed from the log.

**STEP 3: Run the analysis pipeline**

```powershell
cd d:\Projects\Grad\PHCA  
python -u full_analysis.py | Tee-Object -FilePath "experiment_analysis_output.txt"
```

This produces per-pattern comparison tables, global summary, Mann-Whitney U statistical tests, and per-service winner analysis.

**STEP 4: Create a results summary document**

Create `d:\Projects\Grad\PHCA\EXPERIMENT_RESULTS_SUMMARY.md` containing:
1. Test configuration (34 runs, 4 patterns, 7 services, SLO=35.68ms, 12min per run, 30s intervals)
2. The full comparison tables from analysis output 
3. Global metrics (violation rates, latency, resource usage, p-values)
4. Per-pattern breakdown with winners
5. Timestamp of when the suite ran

**STEP 5: Push everything to GitHub**

```powershell
cd d:\Projects\Grad\PHCA
git add -A
git commit -m "Final experiment results: 34-run suite with analysis"
git push origin main
```

**STEP 6: Send completion email**

Send an email to `ahmedd.eldarawi@gmail.com` with subject "PHCA Experiment Results Ready" and body "Congrats! The full 34-run experiment suite completed successfully. Results and analysis have been pushed to GitHub." Use Python smtplib, or if that fails, use the browser to send via Gmail/Outlook web.

**CRITICAL RULES:**
- Do NOT use `--pause-before-start` flag — it causes the script to hang
- If the experiment suite crashes partway, check the log to see which runs completed, then adjust `kafka-structured/experiments/run_config.py` REPETITIONS to only re-run the missing ones
- All commands in the integrated terminal
- My graduation depends on this working

---
