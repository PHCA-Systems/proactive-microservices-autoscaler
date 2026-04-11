# Master Prompt: Complete the Research Paper + Generate Diagram Context Document

---

## Your Role and What You Have

You are completing a graduation research paper for Ahmed El-Darawi and Ahmed Ossama,
supervised by Prof. Ammar Ashraf. You have full access to:
- The paper's LaTeX source file (`.tex`)
- The complete codebase, including all implemented pipeline services
- All documentation files you generated throughout the implementation tasks
- The progress report (February 2026)
- The experiment configuration and run scripts

You are NOT waiting for experiment results. Your job right now is to bring the paper to
~90% completion — every section fully written with precise technical detail — leaving
only the numeric cells of results tables and the chart/graph figures empty (with
placeholders clearly marked). Everything else must be complete, polished, and consistent.

---

## Critical Ground Truth — Read This Before Touching the LaTeX

The following facts are authoritative. Where the existing LaTeX contradicts any of
these, the LaTeX is outdated and must be updated.

### System Identity
- **Title:** Proactive Context-Aware Microservice Autoscaling with Asynchronous ML
  Pub/Sub Architecture
- **Authors:** Ahmed El-Darawi, Ahmed Ossama
- **Supervisor:** Prof. Ammar Ashraf
- **Institution:** [read from existing LaTeX — do not change]
- **SDG alignment:** SDG 9 (Industry, Innovation and Infrastructure), SDG 12
  (Responsible Consumption and Production)

### Deployment Environment (GCP — NOT local, update any local references)
- **Cloud:** Google Cloud Platform (GCP), region `us-central1`
- **Cluster:** Google Kubernetes Engine (GKE), Standard mode
- **Nodes:** 3 × `e2-standard-4` (4 vCPU, 16 GB RAM each)
- **Benchmark:** Sock Shop deployed in namespace `sock-shop`
- **Monitored services (7):** `front-end`, `carts`, `orders`, `catalogue`, `user`,
  `payment`, `shipping`
- **Load generator:** Locust, running on a separate GCE VM (not inside the cluster)
- **Kafka:** Apache Kafka deployed inside the GKE cluster, used as the sole
  inter-service message bus

### SLO Definition
- **SLO threshold:** 36 ms (p95 latency)
- **Derivation:** Computed as the p75 of the p95 latency distribution of the
  `front-end` service under baseline (constant 50-user) load. This is the
  user-facing service with the highest traffic volume. The p75 was chosen as a
  conservative but achievable target — stricter than the mean, not as extreme as
  the p99.
- **Violation definition:** A polling interval is an SLO violation if the
  `front-end` p95 latency exceeds 36 ms.

### Feature Set (11 features per service, polled every 30 seconds)
- `rps` — requests per second
- `cpu_pct` — CPU utilization percentage
- `mem_usage` — memory usage (bytes or MB)
- `p50_latency_ms` — median latency
- `p95_latency_ms` — 95th percentile latency  
- `p99_latency_ms` — 99th percentile latency
- Plus additional latency/error signals collected from the metrics pipeline
- **The `service` feature was deliberately removed** after investigation showed it
  received disproportionate feature importance in tree-based models, causing the
  classifier to learn service identity shortcuts rather than workload patterns.
  Removing it improved generalisation, especially for Logistic Regression. This is
  an ablation finding and must be reported as such.

### Labelling Strategy
- **Method:** Lookahead labelling with a 2-interval (60-second) horizon
- **Label = 1:** if an SLO violation (p95 > 36 ms on `front-end`) occurs within the
  next 2 polling intervals (60 seconds) from the current timestep
- **Label = 0:** otherwise
- **Rationale:** 60 seconds matches the approximate pod startup time on GKE e2
  nodes, meaning a positive prediction at time t gives the scaling controller
  actionable lead time before the violation manifests.
- **Scale-down:** NOT a classification target. Handled entirely by a separate
  policy-based loop (described below).

### Training Dataset
- **Collection environment:** GCP/GKE (same cluster as experiments — NOT local)
- **Total experiments for training data:**
  - Mixed pattern run: 1 × ~4 hours
  - Per-pattern runs: 7 runs each for step, spike, ramp; 4 runs for constant
  - Each run: approximately 10–15 minutes
- **Data schema:** One row per service per polling interval. Features are the 11
  signals above. Label derived via lookahead as described.

### ML Models — Ensemble of Three
All three models are trained on the same GCP-collected dataset, with `service` feature
removed. They operate as independent classifiers publishing votes to the `model-votes`
Kafka topic.

1. **Logistic Regression (LR)**
   - Improved significantly after removing the `service` feature
   - Interpretable linear boundary; serves as the ensemble's regularising member

2. **Random Forest (RF)**
   - Bagged ensemble of decision trees; high variance, low bias
   - Provides robustness to noisy metric signals

3. **XGBoost**
   - Gradient-boosted trees; captures non-linear feature interactions
   - Highest individual accuracy on step and spike patterns

**Ensemble mechanism:** Majority voting. All three classifiers consume from the
`metrics` Kafka topic in parallel, each publishing a binary vote (`SCALE_UP` or
`NO_OP`) to the `model-votes` topic. The Consensus Service subscribes to `model-votes`
and applies majority voting (≥2 of 3 votes = `SCALE_UP`). The final decision is
published to `scaling-decisions`.

**Why these three models:** They have fundamentally different inductive biases —
linear boundary (LR), bagged trees (RF), boosted trees (XGBoost) — meaning their
error modes are uncorrelated, which is exactly the property that makes an ensemble
beneficial. Cite Grinsztajn et al. (NeurIPS 2022) "Why Tree-based Models Still
Outperform Deep Learning on Tabular Data" to preempt the LSTM question.

### Kafka Pipeline Architecture (5 topics / services)

```
[Metrics Collector] ──► metrics topic
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        [LR Classifier] [RF Classifier] [XGB Classifier]
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                      model-votes topic
                              │
                              ▼
                    [Consensus Service]  ◄── majority voting
                              │
                              ▼
                   scaling-decisions topic
                              │
                              ▼
                    [Scaling Controller] ──► Kubernetes API
                              │
                              ▼
                       metrics topic  ◄── [Event Store / InfluxDB]
```

**Kafka topics:**
- `metrics` — raw per-service metric snapshots, published every 30 seconds
- `model-votes` — binary votes from each classifier, keyed by classifier ID
- `scaling-decisions` — final `SCALE_UP` / `NO_OP` decision from consensus service
- (Event store consumes from `metrics` and `scaling-decisions` for persistence)

**Design properties enforced by this architecture:**
- Full decoupling: every service communicates only through Kafka topics
- Hot-swappable classifiers: a new model version can be deployed as a new consumer
  group without stopping the pipeline
- No single point of failure: consensus service can tolerate one classifier going
  offline (2-of-3 still achieves quorum)
- Independent horizontal scaling: each classifier service scales independently

### Scaling Controller — Scale-Up Logic
- **Trigger:** `SCALE_UP` decision received from `scaling-decisions` topic
- **Bottleneck selection:** The service with the highest ratio of
  `current_p95_latency / SLO_threshold` among services not in cooldown. Falls back
  to `front-end` if no metric data is available.
- **Scale quantity:** +1 replica (conservative, symmetric with scale-down)
- **Rationale for +1 over multiplicative:** (a) conservative scaling lets the
  timing advantage of proactive prediction carry the result rather than resource
  aggression; (b) symmetric ±1 policy is interpretable and architecturally clean;
  (c) at Sock Shop's typical replica counts (1–4), +1 is nearly identical to ×1.5
  rounded up for the first two steps; (d) future work can explore adaptive step sizes.
- **Implementation:** Python `kubernetes` client,
  `patch_namespaced_deployment_scale()`, running as a Kubernetes Deployment with a
  dedicated ServiceAccount and ClusterRole (RBAC manifests in `k8s/` directory).

### Scaling Controller — Scale-Down Policy (Rule-Based, NOT ML)
- **Trigger:** Separate polling loop every 30 seconds (independent of Kafka)
- **Conditions (ALL must hold for SCALEDOWN_WINDOW = 10 consecutive intervals):**
  1. CPU utilization < 30% for the service
  2. p95 latency < 0.7 × SLO threshold (25.2 ms) for the service
  3. Current replicas > 1 (minimum replicas floor)
  4. Service not in 5-minute cooldown
- **Scale quantity:** −1 replica
- **Cooldown:** 5 minutes after ANY scale event (up or down) per service. Prevents
  oscillation during pod startup transients.
- **Rationale for rule-based scale-down:** Asymmetric risk profile — premature
  scale-down causes immediate SLO violations, while delayed scale-down only wastes
  resources. Conservative rule-based policy for scale-down avoids the false-negative
  risk of the ML classifier triggering premature resource reclamation.

### Experiment Design

#### Conditions
- **Condition A (Proactive):** Full ML pipeline active. Scaling Controller consuming
  from `scaling-decisions`. HPA disabled.
- **Condition B (Reactive):** Vanilla Kubernetes HPA active, CPU threshold 70%
  (standard in autoscaling literature — cite K8s docs and ERLANG/PBScaler for
  consistency). Scaling Controller pod scaled to 0.

#### Load Patterns and Repetitions
| Pattern | Users / Behaviour | Duration | Repetitions per condition |
|---|---|---|---|
| ConstantLoad | 50 users sustained | 10 min | 3 |
| StepLoad | 50→200→100→300→50 at t=2,4,6,8 min | 10 min | 5 |
| SpikeLoad | Base 10, spikes [15,50,100,25] at t=1,3,5,7 min (30s each) | 10 min | 5 |
| RampLoad | 10→150 over 5 min, sustain 2 min, 150→10 over 3 min | 10 min | 5 |

**Total runs:** (3+5+5+5) × 2 conditions = **36 runs**
**Settling period:** 2 minutes between runs (all deployments reset to 1 replica)
**Total experiment time:** 36 × 12 minutes = ~7.2 hours

**Constant load rationale for reduced repetitions:** ConstantLoad at 50 users
operates below the SLO violation threshold by design — it is the baseline calibration
condition. It is unlikely to generate scaling decisions in either condition. Three
repetitions are sufficient to confirm system stability and establish baseline
resource consumption. Step, spike, and ramp patterns are the scientifically
interesting conditions and receive 5 repetitions each.

#### Run Order
Alternating A/B within each pattern group to control for cluster-level drift
(node warmup, GKE scheduler effects):
For each pattern: A₁, B₁, A₂, B₂, ... , Aₙ, Bₙ

#### Metrics Collected (every 30-second polling interval)
**Primary metrics (hypothesis-bearing):**
1. **SLO violation rate** — fraction of intervals where `front-end` p95 > 36 ms
2. **Total replica-seconds** — Σ(replicas × 30s) across all services and intervals.
   Measures resource consumption. Lower = more efficient.
3. **Time to SLO Recovery (TTSR)** — length in intervals of each violation streak.
   Measures responsiveness once a violation begins.

**Secondary metrics:**
4. Number of scale-up events fired
5. Peak replica count reached (any service)
6. False positive rate of proactive system (SCALE_UP fired when no violation
   occurred in the following 60 seconds)

#### Statistical Analysis
- **Test:** Mann-Whitney U (non-parametric, two-sided, unpaired)
- **Groups:** n=3 (constant) or n=5 (other patterns) per condition per metric
- **Effect size:** Rank-biserial correlation r = 1 − (2U)/(n₁×n₂)
- **Significance threshold:** p < 0.05
- **Report format:** median ± IQR, U statistic, p-value, effect size r
- **Rationale for Mann-Whitney:** SLO violation rate is bounded [0,1] and likely
  skewed; replica-seconds has an asymmetric distribution; normality cannot be assumed
  for n=3 or n=5. Non-parametric test is the correct choice.

---

## Task 1: Complete the LaTeX Paper

### General Instructions
- Read the current `.tex` file in full before making any changes.
- Identify every section that references local deployment, old dataset, or pre-GCP
  conditions and update them to match the ground truth above.
- Do not remove any existing content that is still accurate — supplement and correct,
  do not wholesale replace unless a section is entirely wrong.
- Write in formal academic English. Third person. Past tense for what was done,
  present tense for what the system does architecturally.
- Every design decision must be accompanied by its rationale. A panel will ask "why"
  for every choice — the answer must be in the paper.
- Use `\todo{}` or a clearly marked `% PLACEHOLDER` comment anywhere a number from
  experiment results is needed. Do not invent numbers.

### Sections to Write or Substantially Update

#### Abstract
Rewrite to reflect the complete implemented system. Must mention: proactive ML-based
autoscaling, Kafka pub/sub architecture, ensemble of three classifiers (LR, RF,
XGBoost) with majority voting, GKE deployment, SLO-driven evaluation (36 ms p95),
four load patterns, comparison against reactive HPA baseline. Leave result numbers as
`\todo{fill after experiments}`.

#### 1. Introduction
- Motivate the problem: reactive autoscaling lag, SLO violations under bursty traffic,
  resource overprovisioning from blanket scaling.
- State the gap: existing work scales entire stacks or uses single models; no
  consensus-based hot-swappable ensemble approach with selective per-service scaling.
- State contributions clearly as a numbered list:
  1. A decoupled event-driven pub/sub architecture using Kafka for ML-driven
     proactive autoscaling
  2. A three-model ensemble (LR, RF, XGBoost) with majority-voting consensus,
     enabling fault tolerance and hot-swappability
  3. SLO-driven lookahead labelling methodology for training binary violation
     predictors on live GKE telemetry
  4. Selective per-service bottleneck scaling (not blanket stack scaling)
  5. Empirical evaluation on Sock Shop under four stochastic traffic patterns
     against a reactive HPA baseline

#### 2. Background and Related Work
Ensure coverage of:
- Reactive autoscaling (Kubernetes HPA) and its limitations: cooldown lag, metric
  polling interval, threshold-only logic
- Predictive/proactive autoscaling: LSTM-based approaches, their data requirements,
  inference latency overhead
- ERLANG (EuroSys'24, Sachidananda & Sivaraman): application-aware autoscaling,
  stochastic load methodology — this is the load generator paper we reproduce
- PBScaler (Xie et al., IEEE Trans. Services Computing 2024): bottleneck-aware
  autoscaling, validates our selective scaling approach
- MS-RA (SEAMS 2024): requirements-driven autoscaling on Sock Shop, validates our
  SLO-driven framing
- Grinsztajn et al. (NeurIPS 2022): tabular data, tree models vs. deep learning —
  justifies model selection
- Ensemble methods for fault tolerance in distributed ML pipelines

#### 3. System Architecture
This section must be comprehensive. Structure as follows:

**3.1 Architecture Overview**
Describe the five-component pipeline. Emphasise full decoupling via Kafka topics.
State that no component holds shared state — all state is in the message stream.

**3.2 Kafka Topic Topology**
Describe all topics: `metrics`, `model-votes`, `scaling-decisions`. Include the
message schema for each (field names, types, purpose). Reference your documentation
files for exact schemas.

**3.3 Metrics Collection**
- 7 monitored services, 11 features each, 30-second polling interval
- Feature set: rps, cpu_pct, mem_usage, p50/p95/p99 latency, plus additional signals
- Why OS-level metrics (CPU, memory) alongside application-level (latency, RPS):
  OS metrics lead application metrics under load — they reflect resource saturation
  before it manifests as latency degradation (cite ERLANG for this observation)
- Service feature removal: describe the investigation, the finding (over-weighting
  of service identity), and the decision to remove it. Frame as an ablation.

**3.4 ML Classifier Services**
- Three independent consumer services (LR, RF, XGBoost)
- Each subscribes to `metrics`, runs inference, publishes to `model-votes`
- Hot-swappability: a new model version deploys as a new consumer group;
  old version drains and shuts down without interrupting the pipeline
- Training data: GCP-collected, 4-pattern stochastic workload, lookahead-labelled

**3.5 Consensus Service**
- Subscribes to `model-votes`
- Majority voting: ≥2 of 3 votes = `SCALE_UP`; otherwise `NO_OP`
- Fault tolerance: if one classifier goes offline, 2-of-2 remaining still achieves
  quorum (unanimous agreement required in degraded mode)
- Publishes to `scaling-decisions`

**3.6 Scaling Controller**
- Subscribes to `scaling-decisions`
- Scale-up: bottleneck selection (max p95/SLO ratio) + K8s API call (+1 replica)
- Scale-down: separate 30-second policy loop (rule-based, not ML-driven)
- 5-minute cooldown per service after any scale event
- RBAC: dedicated ServiceAccount with ClusterRole scoped to
  `deployments/scale` patch only
- Why rule-based scale-down: asymmetric risk profile, avoids false-negative
  premature reclamation, prevents thrashing during pod startup transients

**3.7 Event Store**
- Consumes from `metrics` and `scaling-decisions`
- Persists to InfluxDB for audit trail, post-experiment analysis, and future
  closed-loop retraining
- Schema: timestamp, service, all 11 features, decision, replica count

#### 4. SLO Definition and Labelling Methodology
Write this as a dedicated section — it is a methodological contribution.

- Define the SLO: 36 ms p95 latency on `front-end` service
- Derivation: p75 of the distribution of p95 values under 50-user baseline load.
  Justify p75: conservative without being a worst-case outlier; stable across runs.
- Lookahead labelling: formal definition with equation.
  Let `v(t)` = 1 if p95_latency(front-end, t) > SLO, else 0.
  Label `y(t)` = 1 if `v(t+1) OR v(t+2)` = 1, else 0.
  (Where t+1 and t+2 are the next two 30-second intervals = 60-second horizon)
- Rationale for 60-second horizon: matches GKE pod startup time (~30–90s),
  giving the controller actionable lead time before the violation materialises.
- Class imbalance: report the positive class ratio in the training data. Describe
  how class weights or SMOTE were handled (check your codebase for the actual
  approach used).

#### 5. Ensemble Design and Model Selection
- Justify the three-model choice: different inductive biases, uncorrelated errors
- LR: interpretable, regularising member, improved most from feature removal
- RF: variance reduction via bagging, robust to noisy signals
- XGBoost: non-linear interactions, strongest on step/spike patterns
- Report training/validation performance for each model individually and the ensemble.
  Use placeholders for numbers: `\todo{accuracy}, \todo{precision}, \todo{recall},
  \todo{F1}, \todo{AUC-ROC}`
- Ablation: service-feature experiment — model performance before and after removal.
  Table with columns: Model | With service feature | Without service feature | Delta F1
- Majority voting rationale: if individual FPR is p, ensemble FPR under majority
  voting ≈ 3p² − 2p³. Show this formula and plug in your observed individual FPRs.

#### 6. Experimental Methodology
This section describes the experiment design in full. Write it as if a reader needs
to reproduce your results exactly.

**6.1 Infrastructure**
- GCP us-central1, GKE Standard, 3× e2-standard-4 nodes
- Sock Shop benchmark, 11 services, 7 monitored, namespace `sock-shop`
- Locust load generator on separate GCE VM (not inside cluster, avoids resource
  contention with the system under test)
- Kafka co-deployed inside GKE cluster

**6.2 Load Generator**
- Faithful reproduction of ERLANG (EuroSys'24) stochastic methodology
- Purely stochastic: each user selects one action every ~2 seconds independently
- 2-second client-side timeout (models user abandonment, per ERLANG)
- Action distribution table (copy the exact table from the progress report):
  browse_home 21.4%, browse_catalogue 17.1%, browse_category 17.1%,
  view_item 17.1%, add_to_cart 8.5%, view_cart 6.8%, checkout 3.4%
- Sources: Dynamic Yield 2024, Smart Insights 2024, Enhencer 2025,
  Baymard Institute 2024

**6.3 Load Patterns**
Write detailed descriptions of all four patterns with exact parameters as above.
Explain what autoscaling scenario each pattern stress-tests.

**6.4 Experiment Protocol**
- 36 total runs: constant×3, step×5, spike×5, ramp×5 per condition × 2 conditions
- Alternating A/B order within each pattern group
- Pre-run reset: all services to 1 replica, 2-minute stabilisation wait
- Run duration: 10 minutes load + 2 minutes settle
- Condition switching: for proactive, HPA disabled + controller pod active;
  for reactive, controller pod scaled to 0 + HPA applied from manifest

**6.5 Metrics and Statistical Analysis**
Define all primary and secondary metrics formally. State the Mann-Whitney U test
rationale. State significance threshold p < 0.05. Describe the effect size metric.

#### 7. Results
Structure with one subsection per load pattern. Within each subsection:
- Table: metric × condition (proactive median ± IQR vs reactive median ± IQR,
  p-value, effect size r). All cells marked `\todo{}`
- Time-series figure placeholder: `\begin{figure}...[PLACEHOLDER: replica count
  and p95 latency over time, proactive vs reactive, pattern X]...\end{figure}`
- One paragraph of written analysis structure: "The proactive system is expected
  to show [X] because [Y]. The reactive baseline is expected to show [Z] because
  [W]. The most informative metric for this pattern is [M] because [reason]."
  This written structure remains; numbers are placeholders.

#### 8. Discussion
Write this section in full — it does not depend on results numbers, only on what the
design choices imply:
- Why proactive lead time helps most for spike patterns (shortest violation window)
- Why step patterns are where reactive HPA is most vulnerable (sudden discontinuity)
- Why constant load shows negligible difference (neither system needs to scale)
- Trade-off between false positives (unnecessary scale-up, wastes resources) and
  false negatives (missed prediction, SLO violated)
- The +1 replica step size: conservative by design; timing advantage, not resource
  aggression, is the claimed contribution
- Limitations: Sock Shop is a benchmark (not production), single cloud provider,
  fixed SLO threshold, no VPA or cluster autoscaler interaction studied
- Threats to validity: stochastic load means runs are independent but not identical;
  GKE scheduling non-determinism; Kafka consumer lag under high throughput

#### 9. Conclusion and Future Work
Write in full:
- Summarise contributions (restate from introduction, past tense)
- Future work: adaptive step size based on predicted violation severity; online
  retraining from the event store; multi-SLO objectives (latency + cost); extending
  to VPA; testing on larger benchmarks (Online Boutique, Train Ticket)

---

## Task 2: Generate the Diagram Context Document

Create a new file called `diagram_context.md` at the project root. This document is
for a teammate who will be drawing the diagrams in a design tool (draw.io, Figma, or
similar). It must be self-contained — they should not need to read any code.

Structure the document as follows:

---

### DIAGRAM CONTEXT DOCUMENT

**Project:** Proactive Context-Aware Microservice Autoscaling with Asynchronous ML
Pub/Sub Architecture

**Purpose:** This document contains all technical context needed to draw three
architectural diagrams for inclusion in the research paper. Each diagram section
specifies: what the diagram shows, all components and their relationships, visual
groupings, directional flows, labels, and notes on emphasis.

---

#### DIAGRAM 1: Sock Shop Benchmark Architecture

**Purpose in paper:** Shows the benchmark application being tested, so readers
understand what system the autoscaler is managing.

**What it shows:** The Sock Shop e-commerce microservices application — its services,
their roles, and how they interact.

**All 11 services and their roles:**
1. `front-end` — The only user-facing service. Receives all HTTP traffic from users.
   Acts as an API gateway/proxy. Routes to all downstream services. This is the SLO
   measurement point.
2. `catalogue` — Product listing service. Serves product data (names, descriptions,
   images, prices). Backed by `catalogue-db`.
3. `carts` — Shopping cart service. Manages cart state per user. Backed by `carts-db`
   (MongoDB).
4. `orders` — Order processing service. Handles checkout flow. Calls payment and
   shipping. Backed by `orders-db` (MongoDB).
5. `payment` — Payment processing service. Called by orders service. Returns
   authorisation result.
6. `shipping` — Shipping queue service. Publishes shipping jobs to a RabbitMQ queue.
7. `queue-master` — Consumes from the RabbitMQ shipping queue.
8. `user` — User accounts and authentication service. Backed by `user-db` (MongoDB).
9. `catalogue-db` — MongoDB instance for catalogue service.
10. `carts-db` — MongoDB instance for carts service.
11. `orders-db` — MongoDB instance for orders service.
12. `user-db` — MongoDB instance for user service.
13. `rabbitmq` — Message broker used by shipping/queue-master.
14. `session-db` — Redis instance for session management.

**Service call flow (for a typical checkout):**
User → front-end → catalogue (browse) → front-end → carts (add item) → front-end →
orders (checkout) → payment (authorise) + shipping (dispatch) → queue-master

**Visual grouping suggestions:**
- Group stateless services together (front-end, catalogue, carts, orders, payment,
  shipping, queue-master, user) — these are the scalable services
- Group stateful backing stores separately (catalogue-db, carts-db, orders-db,
  user-db, session-db, rabbitmq) — these are NOT autoscaled
- Show `front-end` prominently as the entry point with an arrow from "Users / Locust"
- Use a box or dashed boundary to show "inside GKE cluster, namespace: sock-shop"
- The 7 monitored services (front-end, carts, orders, catalogue, user, payment,
  shipping) should be visually distinguished — e.g. with a different border or
  highlight — labelled "autoscaled + monitored"

**Key label:** "SLO measurement point: p95 latency ≤ 36 ms" on the front-end service.

---

#### DIAGRAM 2: Full System Architecture

**Purpose in paper:** The main architectural diagram. Shows the complete proactive
autoscaling pipeline and how it wraps around Sock Shop.

**Top-level structure:**
Two major zones, clearly bounded:
- Zone A: "Sock Shop (system under test)" — the microservices running in GKE
- Zone B: "Proactive Autoscaling Pipeline" — the Kafka-based ML pipeline

**All components in Zone B (the pipeline) and their relationships:**

**Component 1: Metrics Collector**
- Polls all 7 monitored Sock Shop services every 30 seconds
- Collects: rps, cpu_pct, mem_usage, p50/p95/p99 latency per service
- Publishes to: `metrics` Kafka topic
- Label on arrow: "11 features × 7 services, every 30s"

**Component 2: Apache Kafka (central bus)**
- Three relevant topics to show: `metrics`, `model-votes`, `scaling-decisions`
- All pipeline services communicate ONLY through these topics (no direct calls)
- Visually, Kafka sits at the centre of the pipeline zone
- Show it as a single entity with three named "channels" or "lanes"

**Component 3: LR Classifier Service**
- Subscribes to: `metrics` topic
- Runs: Logistic Regression inference
- Publishes to: `model-votes` topic
- Label: "vote: SCALE_UP / NO_OP"

**Component 4: RF Classifier Service**
- Same as LR but Random Forest
- Subscribes to: `metrics` topic
- Publishes to: `model-votes` topic

**Component 5: XGBoost Classifier Service**
- Same but XGBoost
- Subscribes to: `metrics` topic
- Publishes to: `model-votes` topic

**Show all three classifiers receiving from the same `metrics` topic in parallel
(fan-out pattern). This is a key architectural point.**

**Component 6: Consensus Service**
- Subscribes to: `model-votes` topic
- Logic: majority voting — ≥2 of 3 votes triggers SCALE_UP
- Publishes to: `scaling-decisions` topic
- Label near component: "majority vote (≥ 2/3)"
- Emphasise: this eliminates single point of failure

**Component 7: Scaling Controller**
- Subscribes to: `scaling-decisions` topic
- On SCALE_UP: selects bottleneck service (highest p95/SLO ratio), calls K8s API
  to add +1 replica to that service
- Also runs: independent 30s policy loop for scale-down (CPU < 30% for 10 intervals)
- Calls: Kubernetes API (show as an arrow to Zone A / Sock Shop services)
- Label on K8s API arrow: "+1 replica (scale-up) / −1 replica (scale-down)"
- Label: "5-min cooldown per service"

**Component 8: Event Store (InfluxDB)**
- Consumes from: `metrics` and `scaling-decisions` topics
- Stores: all telemetry + decisions for audit and retraining
- Show as a database icon, slightly separate (it is a side consumer, not on the
  critical path)

**Flow summary for diagram arrows (critical — must be correct):**
```
Sock Shop services ──(poll)──► Metrics Collector ──► [metrics topic]
                                                            │
                                           ┌────────────────┼────────────────┐
                                           ▼                ▼                ▼
                                     LR Classifier    RF Classifier   XGB Classifier
                                           │                │                │
                                           └────────────────┼────────────────┘
                                                            ▼
                                                    [model-votes topic]
                                                            │
                                                            ▼
                                                   Consensus Service
                                                   (majority vote)
                                                            │
                                                            ▼
                                               [scaling-decisions topic]
                                                            │
                                                            ▼
                                                  Scaling Controller
                                                  ┌─────────────────┐
                                                  │  K8s API call   │
                                                  └────────┬────────┘
                                                           ▼
                                              Sock Shop Deployments
                                              (targeted service +1/−1)

[metrics topic] ──► Event Store (InfluxDB)
[scaling-decisions topic] ──► Event Store (InfluxDB)
```

**Additional annotation to include:**
- "Hot-swappable: new classifier version deploys without stopping pipeline"
  (near classifier block)
- "No single point of failure: 2-of-3 quorum maintained if one classifier offline"
  (near consensus service)
- "Selective scaling: only the identified bottleneck service is scaled"
  (near scaling controller → Sock Shop arrow)

---

#### DIAGRAM 3: Experiment Setup (GCP Infrastructure)

**Purpose in paper:** Shows the physical/cloud infrastructure used in experiments,
allowing readers to understand the evaluation environment and reproduce it.

**Top-level: Google Cloud Platform boundary (outer box)**
- Region: us-central1
- Everything below is inside this boundary

**Inside GCP, two main components:**

**Component A: GKE Cluster (Standard Mode)**
- 3 nodes × e2-standard-4 (4 vCPU, 16 GB RAM each) — label the nodes
- Inside the cluster, show two logical namespaces as inner boxes:

  **Namespace: `sock-shop`**
  - Contains: all 11 Sock Shop services (can show as a simple labelled block,
    not individual services — that's Diagram 1's job)
  - Label: "Sock Shop Benchmark (11 services)"
  - Highlight: "7 services monitored + autoscaled"
  - Also contains: Scaling Controller pod (with ServiceAccount icon)
  - Also contains: RBAC ClusterRole binding (can show as a small lock icon)

  **Namespace: `pipeline` (or wherever Kafka and classifiers are deployed —
  check the codebase for actual namespace name)**
  - Contains: Apache Kafka broker
  - Contains: LR Classifier pod, RF Classifier pod, XGBoost Classifier pod
  - Contains: Consensus Service pod
  - Contains: Metrics Collector pod
  - Contains: Event Store / InfluxDB pod

**Component B: GCE Virtual Machine (separate from GKE cluster)**
- Label: "Load Generator VM (GCE)"
- Contains: Locust load testing tool
- Shows 4 traffic patterns: ConstantLoad, StepLoad, SpikeLoad, RampLoad
- Arrow from this VM to the GKE cluster / front-end service:
  Label: "HTTP traffic (stochastic, ERLANG methodology)"

**Key flows to show in this diagram:**
1. Locust VM → front-end service in sock-shop namespace (HTTP load)
2. Metrics Collector → scrapes 7 services in sock-shop namespace → pushes to Kafka
3. Scaling Controller → Kubernetes API Server (inside GKE control plane) → scales
   deployments in sock-shop namespace
4. InfluxDB → "experiment logs (scale_events.jsonl + metric snapshots)" →
   can show a small "Analysis" box outside the cluster representing post-experiment
   Python analysis script

**Additional labels:**
- On the GKE cluster: "GKE Standard Mode, 3× e2-standard-4, us-central1"
- On Kafka: "Apache Kafka (inter-service bus)"
- Somewhere visible: "HPA disabled during Condition A (Proactive)"
  "HPA active (CPU 70%) during Condition B (Reactive)"
- On the experiment: "36 runs total: 3 patterns × 5 reps + constant × 3 reps,
  per condition, alternating A/B order"

**Visual emphasis note:**
The key story this diagram must tell visually is that the load generator is
EXTERNAL to the cluster (avoids resource contention with SUT), the pipeline
and the application share the same GKE cluster but are logically separated by
namespace, and the Scaling Controller is the only component that touches the
Kubernetes API for scaling actions.

---

### End of Diagram Context Document

---

## Final Checklist for Kiro Before Submitting

Before finishing, verify:
- [ ] No section still references "local deployment", "local machine", or
      pre-GCP data collection
- [ ] SLO threshold is consistently 36 ms everywhere it appears
- [ ] Repetitions are consistently: constant=3, step/spike/ramp=5 per condition
- [ ] Total runs stated as 36 everywhere
- [ ] Settling period stated as 2 minutes everywhere
- [ ] Run duration stated as 10 minutes everywhere
- [ ] Scale-up quantity is +1 everywhere (not ×1.5, not ×2)
- [ ] Scale-down conditions are exactly: CPU<30%, p95<25.2ms, 10 consecutive
      intervals, 5-min cooldown
- [ ] The `service` feature removal is mentioned in both the methodology and
      the ensemble design sections
- [ ] All result numbers are `\todo{}` placeholders, not invented
- [ ] `diagram_context.md` is created at project root and is self-contained
- [ ] All citations for external papers are present in the `.bib` file
      (ERLANG EuroSys'24, PBScaler IEEE 2024, MS-RA SEAMS 2024,
      Grinsztajn NeurIPS 2022, K8s HPA docs)
