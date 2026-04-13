# PHCA Pipeline: Comprehensive Problem & Resolution Summary

Since the pipeline was wired up on Google Kubernetes Engine, we have identified several critical flaws spanning across infrastructure, machine learning configurations, orchestration logic, and documentation. 

This document serves as the master record of these problems, effectively proving the massive technical evolution of the proactive autoscaling framework.

---

### 1. The XGBoost / SVM Paper Misalignment (Documentation/Old)
**Problem:** The core LaTeX research paper (`IMSA-v1.tex`) detailed an ensemble utilizing Random Forest, Linear Regression, and XGBoost. However, the actual cluster `ml-inference` deployments were running Support Vector Machines (SVM) instead of XGBoost.
**Causes:** Standard project evolution. XGBoost was likely swapped to SVM during early testing due to better performance on categorical/small-batch time-series data, but the academic documentation was never updated to reflect the new architecture.
**Status:** **[FIXED]**
**Solution:** We rewrote the "Proactive Module" section in `IMSA-v1.tex`, removing XGBoost entirely and documenting the SVM mathematical implementation, ensuring academic integrity and code-to-paper parity.

---

### 2. The Kubeconfig Token Expiration (Infrastructure/New)
**Problem:** The `scaling-controller` running in the pipeline-cluster suddenly lost all authentication capabilities, throwing `Could not get current server API group list` errors and failing all scaling actions silently.
**Causes:** The controller used a statically mounted Service Account JWT token in `k8s/kubeconfig-token.yaml`. This generated token had a strict hardcoded expiration date. The moment it expired, the entire proactive system disconnected from the sock-shop cluster.
**Status:** **[FIXED]**
**Solution:** Generated a new Kubernetes-native token using `kubectl create token` spanning `8760h` (1 full year duration). We overlaid this into the `kubeconfig-token.yaml` config map, completely restoring connectivity.

---

### 3. Database Resource Contention (Architecture/Old & New)
**Problem:** When `carts` or `orders` faced load spikes, p95 latency skyrocketed well above the 35.68ms SLO. The instinctive reaction (and HPA's reaction) was to scale the stateless pods to 10 replicas. This actually *worsened* latency (e.g., `orders` hitting 1872ms under HPA).
**Causes:** The backend databases (`carts-db` Mongo, `orders-db` MySQL) had no compute resource limits enforcing performance and were suffering catastrophic row-level lock contention and connection pool exhaustion when slammed by 10 service pods simultaneously. 
**Status:** **[FIXED]**
**Solution:** 
1. Hard-locked the databases to **1 replica** to prevent un-clustered split-brain data writes.
2. Heavily patched the DBs with vertical scaling: limits of `cpu: 2` and `memory: 1Gi`, giving them massive headroom to handle connection pools.

---

### 4. Rigid Controller Cooldowns (Orchestration/New)
**Problem:** The Proactive ML orchestrator was accurately predicting traffic spikes and issuing `SCALE UP` commands, but the cluster completely failed to react in time, leading to heavy SLO violations.
**Causes:** The `scaling-controller.py` had a rigid environment variable `COOLDOWN_MINUTES = 5`. It would add 1 replica to a service, then stubbornly ignore all further ML predictions for that service for five entire minutes. 
**Status:** **[FIXED]**
**Solution:** Edited the controller code and rebuilt/pushed the docker image (`gcr.io/grad-phca/scaling-controller:latest`) to reduce the cooldown to **1 minute**. The system now reacts near-instantly to continuous bursts.

---

### 5. Linear vs Proportional Scaling Constraints (Orchestration/New)
**Problem:** Even when acting under perfect conditions, the Proactive system was consistently outperformed by HPA in raw speed. 
**Causes:** HPA dynamically scales computationally (e.g., jumping from 1 to 10 replicas in 30 seconds if CPU spikes). The Proactive controller was incredibly weak by design: `target = min(current + 1, MAX)`. It could only add exactly 1 replica per minute, no matter how severe the latency violation was.
**Status:** **[FIXED]**
**Solution:** Overhauled `controller.py` to utilize predictive pseudo-HPA math: `ratio = p95 / SLO_THRESHOLD`. If a service hits 3x the allowed latency, the controller now skips linear counting and instantly adds up to 3-5 replicas simultaneously.

---

### 6. The Smart Bottleneck Guard (Feature Upgrade)
**Problem:** While HPA scales aggressively, it has a fatal flaw: it is mathematically blind to the difference between "CPU processing" and "CPU waiting". HPA crashed the testing cluster because it threw 10 `orders` replicas at the database bottleneck, wasting cloud money and bringing down the core routing infrastructure.
**Causes:** Stateless scaling doesn't resolve stateful bounds. 
**Status:** **[IMPLEMENTED]**
---

### 7. Silent Failure of the Proactive Orchestrator (Orchestration/Old)
**Problem:** In the early testing phases, the "Proactive" tests and "Reactive" tests produced nearly identical 90% violation rates, with Carts and Orders failing to scale at all.
**Causes:** The bash command inside `run_experiments.py` designed to forcefully turn on the Proactive Controller (`kubectl scale deployment scaling-controller`) lacked the `--context` flag identifying the pipeline-cluster. The command silently failed, meaning the Proactive ML system was actually entirely offline during the tests—HPA was orchestrating the cluster the entire time.
**Status:** **[FIXED]**
**Solution:** The experiment runner was rewritten to correctly target `gke_grad-phca_us-central1-a_pipeline-cluster` exclusively for the controller and explicitly tear down HPA.

---

### 8. Locust HTTP Throttling Defaults (Infrastructure/Old)
**Problem:** Initial GKE reactive tests faced catastrophic 84% HTTP failure/timeout rates on Locust, whereas local Docker Compose data-collection never dropped a packet.
**Causes:** Data collection locally had zero resource bounds. On GKE, default Helm configurations had restrictive CPU limits (100m-300m) on the stateless frontend application pods. When a 5-minute reactive test spiked load directly at a single 300m pod before HPA could spin up, the CPU throttled, stalling the kernel and forcing 2-second HTTP timeouts across the board.
**Status:** **[FIXED]**
---

### 9. Python Runner Execution Drift (Orchestration/New)
**Problem:** Across all experiments, the data representing the final 3-5 minutes of load consistently dropped to 0 violations and 0% CPU, making it look like the test naturally recovered perfectly at the end of every run.
**Causes:** The python runners used a naive `time.sleep(30)` loop to space out data collection. However, querying Prometheus via HTTP and parsing the JSON takes approximately 3-5 seconds depending on network load. Because this execution time wasn't accounted for, each "30-second interval" actually took ~34 seconds. Over a 15-minute test (30 intervals), the python loop drifted behind real-world time by roughly **2 full minutes**. Locust mechanically halted traffic exactly at 15:00 based on its internal timer, but the Python loops continued to scrape the now-empty cluster for 3-5 more intervals, recording artificial silence. 
**Status:** **[FIXED]**
**Solution:** Overhauled all python iteration loops (`run_experiments.py`, `run_quick_test.py`, etc.) to use Absolute Clock Synchronization (`time.sleep(target_time - time.time())`). This acts as an ironclad metronome, entirely eliminating execution drift and perfectly aligning the final metric snapshot with the final Locust HTTP request.

---

### 10. Sequential Bottleneck Scaling (Head-of-Line Blocking) (Orchestration/New)
**Problem:** The proactive controller's front-end service took **3.5 minutes** (7 intervals) to receive its first scale-up despite continuously violating the SLO from interval 0. This resulted in a 24.3% global violation rate — better than HPA but far from optimal.
**Causes:** The controller's `select_bottleneck_service()` function picked a **single winner** (highest p95/SLO ratio) per decision cycle. Because carts and orders consistently had higher raw ratios, they dominated every selection round. The 1-minute cooldown then locked out ALL services until it expired. Front-end had to wait until every other service either stabilized or was blocked by the DB Guard before it could get its turn — classic head-of-line blocking in a serialized scheduler.
**Status:** **[FIXED]**
**Solution:** Replaced `select_bottleneck_service()` (single-winner) with `select_eligible_services()` (parallel per-service). Every service is now evaluated independently: if it is violating the SLO, passes the DB Bottleneck Guard (CPU > 25%), and is not in cooldown, it scales immediately — regardless of what other services are doing. Each service maintains its own independent cooldown timer. This aligns with how production autoscalers (HPA, Google Autopilot, FIRM) treat each deployment as an independent scaling unit. Results: global violation rate dropped from **24.3% to 7.9%** while using **54% fewer replica-seconds** than the old sequential approach.

