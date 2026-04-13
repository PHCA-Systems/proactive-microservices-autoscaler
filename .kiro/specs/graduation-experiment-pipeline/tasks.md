# Implementation Plan: Graduation Experiment Pipeline

## Overview

This plan implements an automated orchestration system for executing a 34-run experiment suite comparing proactive vs reactive autoscaling. The implementation leverages existing scripts (`run_experiments.py`, `full_analysis.py`) and adds orchestration, monitoring, verification, documentation, and notification capabilities. All code will be written in Python with PowerShell integration for Windows environment.

## Tasks

- [x] 1. Run infrastructure validation
  - Validate Prometheus endpoint (`http://34.170.213.190:9090`)
  - Validate Locust VM SSH connectivity (`35.222.116.125`)
  - Validate Kubernetes cluster connectivity (`kubectl cluster-info`)
  - Validate Sock Shop endpoint (`http://104.154.246.88`)
  - Ensure all infrastructure is ready before experiments
  - _Requirements: Design "validateInfrastructure()" function specification_

- [x] 2. **RUN THE 34-RUN EXPERIMENT SUITE** (~7 hours)
  - Execute: `cd kafka-structured/experiments && python -u run_experiments.py 2>&1 | Tee-Object -FilePath "experiment_run_log.txt"`
  - NO `--pause-before-start` flag
  - Monitor progress periodically by tailing the log file
  - Let it run to completion (34 runs x ~12 min each = ~7 hours)
  - Do NOT interact with stdin - just monitor
  - _Requirements: MASTER_EXECUTION_PLAN.md "LAUNCH COMMAND" section_

- [x] 3. Verify all 34 result files exist
  - Count `.jsonl` files in `kafka-structured/experiments/results/` directory
  - Exclude files starting with `diag_*` from count
  - Expected count: 34
  - Identify any missing runs if count < 34
  - _Requirements: MASTER_EXECUTION_PLAN.md "POST-EXPERIMENT: Verify & Analyze" section_

- [x] 4. Run statistical analysis pipeline
  - Execute: `cd d:\Projects\Grad\PHCA && python -u full_analysis.py | Tee-Object -FilePath "experiment_analysis_output.txt"`
  - Produces per-pattern comparison tables
  - Generates global summary with violation rates, latency, resource usage
  - Performs Mann-Whitney U statistical tests
  - Creates per-service winner analysis
  - _Requirements: MASTER_EXECUTION_PLAN.md "POST-EXPERIMENT: Verify & Analyze" section_

- [x] 5. Create EXPERIMENT_RESULTS_SUMMARY.md
  - Create summary document at `d:\Projects\Grad\PHCA\EXPERIMENT_RESULTS_SUMMARY.md`
  - Include test configuration (34 runs, 4 patterns, 7 services, SLO=35.68ms)
  - Include full comparison tables from analysis output
  - Include global metrics (violation rates, latency, resource usage, p-values)
  - Include per-pattern breakdown with winners
  - Include timestamp of when suite ran
  - _Requirements: MASTER_EXECUTION_PLAN.md "POST-EXPERIMENT: Verify & Analyze" section_

- [-] 6. Push results to GitHub
  - Execute: `git add -A`
  - Execute: `git commit -m "Final experiment results: 34-run suite complete with analysis"`
  - Execute: `git push origin main`
  - Verify push succeeded
  - _Requirements: MASTER_EXECUTION_PLAN.md "POST-EXPERIMENT: Verify & Analyze" section_

- [ ] 7. Send completion email
  - Send email to `ahmedd.eldarawi@gmail.com`
  - Subject: "PHCA Experiment Results Ready"
  - Body: "Congrats! The full 34-run experiment suite completed successfully. Results and analysis have been pushed to GitHub."
  - Use Python smtplib or fallback to browser-based email
  - _Requirements: MASTER_EXECUTION_PLAN.md "POST-EXPERIMENT: Verify & Analyze" section_

## Notes

- This task list follows the MASTER_EXECUTION_PLAN.md checklist exactly
- Task 2 is the critical 7-hour experiment run - do NOT interrupt it
- All subsequent tasks depend on Task 2 completing successfully
- The pipeline is designed for unattended overnight execution
- If experiments fail partway, check the log to identify which runs completed
