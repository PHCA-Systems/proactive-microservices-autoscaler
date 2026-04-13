# MASTER EXECUTION PLAN — Full 34-Run Experiment Suite

> **CRITICAL: This is a graduation-grade overnight run. There are NO do-overs. Follow every step precisely.**

---

## Context & Current State

This is a Proactive ML-based Microservices Autoscaler (PHCA) graduation project. The system has been debugged, improved, and validated over multiple sessions. All 10 critical bugs have been fixed (see `phca_problems_summary.md` in root). The codebase has been pushed to GitHub. The system is ready for the final 34-run experiment sweep.

### What Was Already Done (DO NOT REDO)
- ✅ Codebase pushed to GitHub (`git push origin main --force` completed successfully)
- ✅ `phca_problems_summary.md` copied to codebase root with all 10 problems documented
- ✅ `.gitignore` updated to exclude `old_AI_analysis_logs/` and temp scripts
- ✅ Old investigation MDs removed from git tracking
- ✅ `run_config.py` updated: REPETITIONS = constant:2, step:5, spike:5, ramp:5 (= 34 runs)
- ✅ `run_experiments.py` fixed: execution drift fix (absolute clock sync), n_intervals = 12
- ✅ `controller.py` deployed with parallel per-service scaling (rebuilt + pushed to GCR + rolled out)
- ✅ Locust VM verified reachable at `35.222.116.125`

### Infrastructure Details
- **Target Cluster:** `gke_grad-phca_us-central1-a_sock-shop-cluster` (Sock Shop app)
- **Pipeline Cluster:** `gke_grad-phca_us-central1-a_pipeline-cluster` (ML pipeline + controller)
- **Prometheus:** `http://34.170.213.190:9090`
- **Locust VM:** `35.222.116.125` (SSH user: `User`, key: `~/.ssh/google_compute_engine`)
- **Sock Shop External IP:** `104.154.246.88`
- **SLO Threshold:** `35.68ms` (p95 latency)
- **Controller Image:** `gcr.io/grad-phca/scaling-controller:latest` (parallel scaling version)

---

## THE EXECUTION PIPELINE

### Phase 0: Pre-Flight Checks (5 minutes)

Run these checks. ALL must pass before proceeding:

```powershell
# 1. Locust VM reachable
ssh -i $env:USERPROFILE/.ssh/google_compute_engine -o StrictHostKeyChecking=no User@35.222.116.125 "echo LOCUST_OK"

# 2. Prometheus reachable
python -c "import requests; r=requests.get('http://34.170.213.190:9090/api/v1/query',params={'query':'up'},timeout=5); print('PROM_OK' if r.status_code==200 else 'FAIL')"

# 3. Scaling controller running on pipeline cluster
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster get pods -n kafka -l app=scaling-controller

# 4. All Sock Shop pods healthy
kubectl --context=gke_grad-phca_us-central1-a_sock-shop-cluster get pods -n sock-shop

# 5. Verify 34-run schedule
cd d:\Projects\Grad\PHCA\kafka-structured\experiments
python -c "from run_config import generate_run_schedule; s=generate_run_schedule(); print(f'Total runs: {len(s)}')"
# Expected output: Total runs: 34

# 6. Verify no crash on import
python -c "import run_experiments; print('IMPORT_OK')"
```

### Phase 1: Launch the Full 34-Run Suite (~7.1 hours)

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments
python -u run_experiments.py --pause-before-start 2>&1 | Tee-Object -FilePath "experiment_run_log.txt"
```

**Timing:**
- Each run: ~6 min load + 2 min settle + 2 min reset = ~10 min
- 34 runs × 10 min = ~340 minutes = **~5.7 hours**
- If started at 5:30 AM Cairo → estimated finish: **~11:15 AM Cairo**

**What to monitor:**
- The script prints progress like `[RUN 01/34] proactive_constant_run01`
- Each run saves a `.jsonl` file to `kafka-structured/experiments/results/`
- If it crashes, check the error, fix it, and note which run it crashed on
- You can restart from a specific run by modifying `run_config.py` REPETITIONS or editing the schedule

**If Locust SSH fails mid-run:** The SSH connection to the Locust VM can be flaky. If a run fails with an SSH error, just retry. The experiment runner should handle this gracefully.

**If Prometheus times out:** Prometheus queries occasionally timeout. The collector returns 0.0 for failed queries. A few zeros are acceptable; a full run of zeros means Prometheus is down.

### Phase 2: Verify Results (5 minutes)

After the suite completes, verify all 34 files exist:

```powershell
cd d:\Projects\Grad\PHCA\kafka-structured\experiments\results
Get-ChildItem *.jsonl | Measure-Object
# Expected: Count = 34 (plus any diag_ files from earlier tests)

# Check that files are non-empty
Get-ChildItem *.jsonl | Where-Object { $_.Length -lt 100 }
# Expected: nothing (all files should be >100 bytes)
```

Expected filenames follow the pattern:
- `proactive_constant_run01.jsonl`, `reactive_constant_run01.jsonl`
- `proactive_step_run01.jsonl`, `reactive_step_run01.jsonl`
- etc.

### Phase 3: Run Academic Analysis Pipeline

Create and run this analysis script. It computes ALL the metrics needed for the paper:

```python
#!/usr/bin/env python3
"""
Full Academic Analysis Pipeline
Processes all 34 experiment runs and generates paper-ready comparison tables.
"""
import json
import os
from pathlib import Path
from collections import defaultdict

try:
    from scipy import stats
except ImportError:
    import subprocess
    subprocess.run(["python", "-m", "pip", "install", "scipy"], check=True)
    from scipy import stats

RESULTS_DIR = Path("kafka-structured/experiments/results")
MONITORED = ["front-end", "carts", "orders", "catalogue", "user", "payment", "shipping"]
SLO = 35.68
PATTERNS = ["constant", "step", "spike", "ramp"]

def load_run(filepath):
    """Load JSONL, filtering out settle-phase snapshots."""
    data = []
    for line in open(filepath):
        snap = json.loads(line)
        if snap.get("phase") != "settle":
            data.append(snap)
    return data

def analyze_run(data):
    """Compute per-service metrics for a single run."""
    results = {}
    for svc in MONITORED:
        violations = sum(1 for s in data if s["services"][svc]["p95_ms"] > SLO)
        vr = violations / len(data) * 100 if data else 0
        p95_vals = [s["services"][svc]["p95_ms"] for s in data if s["services"][svc]["p95_ms"] > 0]
        avg_p95 = sum(p95_vals) / len(p95_vals) if p95_vals else 0
        max_p95 = max(p95_vals) if p95_vals else 0
        rep_secs = sum(s["services"][svc].get("replicas", 1) * 30 for s in data)
        max_reps = max(s["services"][svc].get("replicas", 1) for s in data)
        results[svc] = {
            "violation_rate": vr,
            "avg_p95": avg_p95,
            "max_p95": max_p95,
            "replica_seconds": rep_secs,
            "max_replicas": max_reps,
            "p95_values": p95_vals,
            "violations": violations,
            "total_intervals": len(data),
        }
    return results

# Collect all runs
pro_runs = defaultdict(list)  # pattern -> [run_results]
rea_runs = defaultdict(list)

for f in sorted(RESULTS_DIR.glob("*.jsonl")):
    name = f.stem
    if name.startswith("diag_"):
        continue  # Skip diagnostic runs
    parts = name.split("_")
    if len(parts) < 3:
        continue
    condition = parts[0]  # proactive or reactive
    pattern = parts[1]    # constant, step, spike, ramp
    data = load_run(f)
    if not data:
        print(f"WARNING: Empty file {f.name}")
        continue
    results = analyze_run(data)
    if condition == "proactive":
        pro_runs[pattern].append(results)
    elif condition == "reactive":
        rea_runs[pattern].append(results)

print("\n" + "=" * 120)
print("  FULL EXPERIMENT RESULTS — 34-Run Academic Analysis")
print("=" * 120)

# Per-pattern analysis
for pattern in PATTERNS:
    pro_list = pro_runs.get(pattern, [])
    rea_list = rea_runs.get(pattern, [])
    if not pro_list or not rea_list:
        print(f"\n  [SKIP] {pattern}: no data (pro={len(pro_list)}, rea={len(rea_list)})")
        continue

    print(f"\n{'='*120}")
    print(f"  PATTERN: {pattern.upper()} ({len(pro_list)} proactive runs, {len(rea_list)} reactive runs)")
    print(f"{'='*120}")
    print(f"  {'Service':<12} | {'Pro VR%':>9} | {'Rea VR%':>9} | {'Pro p95':>9} | {'Rea p95':>9} | {'Pro RepSec':>10} | {'Rea RepSec':>10} | {'MW-U p':>10} | {'Winner'}")
    print("  " + "-" * 108)

    for svc in MONITORED:
        # Average across runs
        pro_vrs = [r[svc]["violation_rate"] for r in pro_list]
        rea_vrs = [r[svc]["violation_rate"] for r in rea_list]
        pro_p95s = [r[svc]["avg_p95"] for r in pro_list]
        rea_p95s = [r[svc]["avg_p95"] for r in rea_list]
        pro_reps = [r[svc]["replica_seconds"] for r in pro_list]
        rea_reps = [r[svc]["replica_seconds"] for r in rea_list]

        avg_pro_vr = sum(pro_vrs) / len(pro_vrs)
        avg_rea_vr = sum(rea_vrs) / len(rea_vrs)
        avg_pro_p95 = sum(pro_p95s) / len(pro_p95s)
        avg_rea_p95 = sum(rea_p95s) / len(rea_p95s)
        avg_pro_rep = sum(pro_reps) / len(pro_reps)
        avg_rea_rep = sum(rea_reps) / len(rea_reps)

        # Mann-Whitney U test on violation rates
        p_str = "N/A"
        if len(pro_vrs) >= 2 and len(rea_vrs) >= 2:
            try:
                stat, pval = stats.mannwhitneyu(pro_vrs, rea_vrs, alternative='two-sided')
                p_str = f"{pval:.4f}"
                if pval < 0.05:
                    p_str += " *"
            except ValueError:
                p_str = "Tied"

        winner = "TIE"
        if avg_pro_vr < avg_rea_vr - 1:
            winner = "PROACTIVE"
        elif avg_rea_vr < avg_pro_vr - 1:
            winner = "REACTIVE"

        print(f"  {svc:<12} | {avg_pro_vr:>8.1f}% | {avg_rea_vr:>8.1f}% | {avg_pro_p95:>7.1f}ms | {avg_rea_p95:>7.1f}ms | {avg_pro_rep:>10.0f} | {avg_rea_rep:>10.0f} | {p_str:>10} | {winner}")

# Global summary across ALL patterns
print(f"\n{'='*120}")
print(f"  GLOBAL SUMMARY (All Patterns Combined)")
print(f"{'='*120}")

all_pro_vr, all_rea_vr = [], []
all_pro_p95, all_rea_p95 = [], []
total_pro_reps, total_rea_reps = 0, 0

for pattern in PATTERNS:
    for run in pro_runs.get(pattern, []):
        for svc in MONITORED:
            all_pro_vr.append(run[svc]["violation_rate"])
            all_pro_p95.append(run[svc]["avg_p95"])
            total_pro_reps += run[svc]["replica_seconds"]
    for run in rea_runs.get(pattern, []):
        for svc in MONITORED:
            all_rea_vr.append(run[svc]["violation_rate"])
            all_rea_p95.append(run[svc]["avg_p95"])
            total_rea_reps += run[svc]["replica_seconds"]

if all_pro_vr and all_rea_vr:
    g_pro_vr = sum(all_pro_vr) / len(all_pro_vr)
    g_rea_vr = sum(all_rea_vr) / len(all_rea_vr)
    g_pro_p95 = sum(all_pro_p95) / len(all_pro_p95)
    g_rea_p95 = sum(all_rea_p95) / len(all_rea_p95)

    stat, pval = stats.mannwhitneyu(all_pro_vr, all_rea_vr, alternative='two-sided')
    p_str = f"{pval:.6f}"
    if pval < 0.05:
        p_str += " ***"

    print(f"  Proactive Global Violation Rate: {g_pro_vr:.1f}%")
    print(f"  Reactive  Global Violation Rate: {g_rea_vr:.1f}%")
    print(f"  Violation Reduction:             {g_rea_vr - g_pro_vr:.1f} percentage points")
    print(f"  Proactive Mean p95:              {g_pro_p95:.1f}ms")
    print(f"  Reactive  Mean p95:              {g_rea_p95:.1f}ms")
    print(f"  Latency Improvement:             {((g_rea_p95 - g_pro_p95) / g_rea_p95 * 100):.1f}%")
    print(f"  Proactive Replica-Seconds:       {total_pro_reps}")
    print(f"  Reactive  Replica-Seconds:       {total_rea_reps}")
    print(f"  Resource Savings:                {(1 - total_pro_reps / total_rea_reps) * 100:.1f}%")
    print(f"  Mann-Whitney U p-value:          {p_str}")
    print(f"  Statistically Significant:       {'YES' if pval < 0.05 else 'NO'}")

print(f"\n{'='*120}")
```

Save this as `d:\Projects\Grad\PHCA\full_analysis.py` and run:

```powershell
cd d:\Projects\Grad\PHCA
python full_analysis.py | Tee-Object -FilePath "experiment_analysis_output.txt"
```

### Phase 4: Create Results Summary Document

After analysis completes, create a `EXPERIMENT_RESULTS_SUMMARY.md` in the project root containing:
1. Test configuration (34 runs, 4 patterns, 7 services, SLO=35.68ms)
2. The full comparison tables from the analysis output
3. Global metrics (violation rates, latency, resource usage, p-values)
4. Per-pattern breakdown
5. Key findings

### Phase 5: Final GitHub Push

```powershell
cd d:\Projects\Grad\PHCA
git add -A
git commit -m "Final experiment results: 34-run suite complete with analysis"
git push origin main
```

### Phase 6: Send Email Notification

Use Python to send the email:

```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Congrats! The full 34-run experiment suite has completed successfully. All results and analysis have been pushed to GitHub. Check the EXPERIMENT_RESULTS_SUMMARY.md in the repository root for the full breakdown.")
msg["Subject"] = "PHCA Experiment Suite Complete"
msg["From"] = "phca.experiments@gmail.com"
msg["To"] = "ahmedd.eldarawi@gmail.com"

# Note: You may need to use an app password or alternative SMTP.
# If SMTP fails, use the browser to send the email manually via Gmail.
```

If SMTP doesn't work, use the browser tool to navigate to Gmail and compose the email manually to `ahmedd.eldarawi@gmail.com`.

---

## PROMPT TO GIVE THE NEXT AI SESSION

Copy-paste this into a new AI session to continue execution:

---

```
I am running my graduation project's final experiments. Everything is set up and the codebase 
is at d:\Projects\Grad\PHCA. Read the file MASTER_EXECUTION_PLAN.md in the project root — 
it contains the complete step-by-step instructions for what you need to do.

Here is what has ALREADY been completed:
- All code fixes applied and deployed (parallel scaling controller, clock sync, DB guard)
- Codebase pushed to GitHub
- phca_problems_summary.md with 10 documented bugs is in the root
- run_config.py set to full 34-run schedule
- .gitignore updated, old MDs removed from git

Your job is to execute the remaining steps from MASTER_EXECUTION_PLAN.md:
1. Run pre-flight checks (Phase 0)
2. Launch the full 34-run experiment suite and monitor it like a hawk (Phase 1)
3. Verify all 34 result files exist (Phase 2)
4. Run the academic analysis pipeline (Phase 3) — the full_analysis.py script is in the plan
5. Create EXPERIMENT_RESULTS_SUMMARY.md (Phase 4)
6. Push everything to GitHub (Phase 5)
7. Send email to ahmedd.eldarawi@gmail.com saying results are ready (Phase 6)

CRITICAL RULES:
- If something breaks, identify what succeeded, fix the issue, and restart from where it failed
- Track and log EVERYTHING — start times, ETAs, completion times
- All output files must be organized and properly named
- Run all commands in the integrated terminal, not background tasks
- The experiment runner is at: d:\Projects\Grad\PHCA\kafka-structured\experiments\run_experiments.py
- Results go to: d:\Projects\Grad\PHCA\kafka-structured\experiments\results\
- The estimated runtime is ~5.7 hours for 34 runs

DO NOT skip any verification steps. My graduation depends on this.
```

---

## KEY FILES REFERENCE

| File | Purpose |
|------|---------|
| `kafka-structured/experiments/run_experiments.py` | Main experiment runner (34 runs) |
| `kafka-structured/experiments/run_config.py` | Schedule config (patterns × repetitions) |
| `kafka-structured/experiments/run_diagnostic_test.py` | Diagnostic test runner (used for validation) |
| `kafka-structured/services/scaling-controller/controller.py` | The proactive controller (parallel scaling) |
| `kafka-structured/k8s/hpa-baseline.yaml` | HPA config for reactive baseline |
| `kafka-structured/k8s/kubeconfig-token.yaml` | Cross-cluster auth token |
| `phca_problems_summary.md` | Master document of all 10 bugs found and fixed |
| `Paper/IMSA-v1.tex` | The LaTeX research paper |

## WHAT DATA WE ARE COLLECTING

For each of the 34 runs, every 30 seconds across 7 services, we collect:
1. **Replica Count** — how many pods are running
2. **p95 Latency (ms)** — 95th percentile response time
3. **CPU Utilization (%)** — total CPU pressure
4. **SLO Violation (bool)** — p95 > 35.68ms

The analysis pipeline then computes:
1. **SLO Violation Rate** — % of intervals violating per service/pattern
2. **Mean p95 Latency** — average response time
3. **Replica-Seconds** — total compute used (replicas × 30s × intervals)
4. **Mann-Whitney U p-value** — statistical significance test
5. **Per-pattern winner** — which system wins each load pattern
6. **Global summary** — overall winner across all 34 runs

## PREVIOUS VALIDATION RESULTS (for reference)

Latest 150-user constant 10-minute head-to-head (after parallel scaling fix):

| Metric | Proactive | Reactive HPA |
|--------|-----------|-------------|
| Global Violation Rate | **7.9%** | 45.0% |
| Front-end Violations | 15.0% | 35.0% |
| Carts Violations | 30.0% | 75.0% |
| Orders Violations | 10.0% | 90.0% |
| Total Replica-Seconds | 4,740 | 17,280 |
| Resource Savings | **72.6% fewer** | baseline |
| Services Won | **6/7** | 0/7 (1 tie) |
