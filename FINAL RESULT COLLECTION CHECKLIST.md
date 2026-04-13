# Full Experiment Suite Execution - Mission Critical

## Phase 0: Pre-Flight
- [ ] Copy phca_problems_summary.md to codebase root
- [ ] Verify .gitignore excludes old_AI_analysis_logs
- [ ] Remove old_AI_analysis_logs from git tracking if present
- [ ] Push entire codebase to GitHub (force overwrite)
- [ ] Verify push succeeded

## Phase 1: Final Verification
- [ ] Verify run_config.py has correct 34-run schedule
- [ ] Verify run_experiments.py has no crash bugs
- [ ] Verify Locust VM is reachable
- [ ] Verify Prometheus is reachable
- [ ] Verify scaling-controller has parallel scaling deployed
- [ ] Verify cluster is healthy (all pods running)
- [ ] Dry-run validation of experiment runner

## Phase 2: Execute Full 34-Run Suite
- [ ] Clear old results from results directory
- [ ] Record exact start time
- [ ] Launch experiment suite
- [ ] Monitor every run for failures
- [ ] Log progress checkpoints
- [ ] Record exact end time

## Phase 3: Post-Experiment Analysis
- [ ] Verify all 34 JSONL files exist and are non-empty
- [ ] Run academic analysis pipeline (per-service, global, statistical)
- [ ] Generate comparison tables
- [ ] Generate summary statistics

## Phase 4: Documentation & Delivery
- [ ] Create comprehensive results summary document
- [ ] Push all results + summary to GitHub
- [ ] Send completion email to ahmedd.eldarawi@gmail.com
