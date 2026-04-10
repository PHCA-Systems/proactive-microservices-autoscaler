### Master Notes:

\- It's not required to have the same folder structure outlined below, this output is from a claude chat session. You have codebase context and should follow the folder structure in a way that makes sense

\- The kafka pipeline should already exist and be working (check services folder), my gradmate said it was only missing the final model after choosing. So firstly verify this and then plug in the models I outline in the point below. Only rework the pipeline if its not working

\- After all the model experiments (which you can find in the ML-Models folder) , the best models and the ones that we will use for the system are the Gke mixed patterns models with standard 80 20 split (not leave one out) , so navigate the folders and youll find the 3 versions of the LR,xgb, and randforest that match what I said

\- you don't have to use the code copy paste, again you have the codebase structure so adjust accordingly.

\- this is obvious but my pipeline will work all on the cloud , in order to compare my sockshop deployment being scaled using HPA vs my solution

\- the kafka topic names may not match whats written in this spec , the codebase is always right

\- Again as with everything, work within a venv. Use the existing one to save time.

\- I want to see everything that is currently being worked on, current task etc...

\- When we reach the part right before overnight runs , pause for a second so we can communicate and make sure everything is ready to go.

\- Document only what is necessary for my paper, no LLM bs

\- DO NOT USE MSYS Python -- This will not work and waste a lot of time





Spec: Proactive Autoscaler — End-to-End Integration \& Evaluation

## Context

This is a graduation research project implementing a proactive, context-aware microservice
autoscaling system. The architecture uses Apache Kafka as a pub/sub backbone. Three ML
classifiers (Logistic Regression, Random Forest, XGBoost) each consume metrics from a
`metrics` Kafka topic, publish votes to a `model-votes` topic, and a consensus service
aggregates votes via majority voting and publishes `SCALE\\\_UP` or `NO\\\_OP` decisions to a
`scaling-decisions` topic.

The Kafka consumer pipeline is already built and working. The inference service reads from
`scaling-decisions` and produces a final decision. **What does not exist yet:**

* The Scaling Controller (K8s API calls)
* The scale-down policy loop
* The experiment runner (automated 40-run orchestration)
* The reactive HPA baseline configuration
* The results analyser

The system is deployed on GKE (us-central1), 3× e2-standard-4 nodes. Sock Shop benchmark
is deployed in the `sock-shop` namespace. The 7 monitored services are:
`front-end`, `carts`, `orders`, `catalogue`, `user`, `payment`, `shipping`.

SLO threshold: **36ms** (p95 latency of front-end service, p75 of baseline runs).
Polling interval: **30 seconds**.
Lookahead window used for labelling: **2 intervals (60 seconds)**.

\---

## Part 1 — Scaling Controller Service

### 1.1 RBAC Manifest

Create file `k8s/scaling-controller-rbac.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: scaling-controller-sa
  namespace: sock-shop
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: scaling-controller-role
rules:
- apiGroups: \\\["apps"]
  resources: \\\["deployments", "deployments/scale"]
  verbs: \\\["get", "list", "patch", "update"]
- apiGroups: \\\[""]
  resources: \\\["pods"]
  verbs: \\\["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scaling-controller-binding
subjects:
- kind: ServiceAccount
  name: scaling-controller-sa
  namespace: sock-shop
roleRef:
  kind: ClusterRole
  name: scaling-controller-role
  apiGroup: rbac.authorization.k8s.io
```

Apply with: `kubectl apply -f k8s/scaling-controller-rbac.yaml`

### 1.2 Scaling Controller — Core Logic

Create `scaling\\\_controller/controller.py`. This service:

1. Consumes from the `scaling-decisions` Kafka topic
2. On `SCALE\\\_UP`: identifies the bottleneck service, computes target replicas (+1), executes
3. On a separate polling loop every 30s: checks scale-down conditions for all services
4. Enforces a 5-minute cooldown after any scale event per service
5. Logs every decision with timestamp, service, direction, old replicas, new replicas

```python
import os
import json
import logging
import time
from datetime import datetime, timedelta
from math import ceil
from confluent\\\_kafka import Consumer, KafkaError
from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s \\\[%(levelname)s] %(message)s"
)
log = logging.getLogger(\\\_\\\_name\\\_\\\_)

# ── Configuration ────────────────────────────────────────────────────────────
NAMESPACE          = os.getenv("NAMESPACE", "sock-shop")
KAFKA\\\_BOOTSTRAP    = os.getenv("KAFKA\\\_BOOTSTRAP\\\_SERVERS", "localhost:9092")
DECISIONS\\\_TOPIC    = os.getenv("DECISIONS\\\_TOPIC", "scaling-decisions")
METRICS\\\_TOPIC      = os.getenv("METRICS\\\_TOPIC", "metrics")
SLO\\\_THRESHOLD\\\_MS   = float(os.getenv("SLO\\\_THRESHOLD\\\_MS", "36.0"))
COOLDOWN\\\_MINUTES   = int(os.getenv("COOLDOWN\\\_MINUTES", "5"))
MIN\\\_REPLICAS       = int(os.getenv("MIN\\\_REPLICAS", "1"))
MAX\\\_REPLICAS       = int(os.getenv("MAX\\\_REPLICAS", "10"))
SCALEDOWN\\\_CPU\\\_PCT  = float(os.getenv("SCALEDOWN\\\_CPU\\\_PCT", "30.0"))
SCALEDOWN\\\_LAT\\\_RATIO= float(os.getenv("SCALEDOWN\\\_LAT\\\_RATIO", "0.7"))  # p95 < 0.7×SLO
SCALEDOWN\\\_WINDOW   = int(os.getenv("SCALEDOWN\\\_WINDOW", "10"))  # consecutive intervals

MONITORED\\\_SERVICES = \\\[
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

# ── State ────────────────────────────────────────────────────────────────────
# last\\\_scale\\\_event\\\[service] = datetime of last scale action
last\\\_scale\\\_event: dict\\\[str, datetime] = {}

# recent\\\_metrics\\\[service] = list of last N metric dicts (rolling window)
recent\\\_metrics: dict\\\[str, list] = {s: \\\[] for s in MONITORED\\\_SERVICES}

# ── Kubernetes client ────────────────────────────────────────────────────────
def init\\\_k8s():
    try:
        config.load\\\_incluster\\\_config()
        log.info("Loaded in-cluster K8s config")
    except Exception:
        config.load\\\_kube\\\_config()
        log.info("Loaded local kubeconfig")
    return client.AppsV1Api()

apps\\\_v1 = init\\\_k8s()

# ── Helpers ──────────────────────────────────────────────────────────────────
def get\\\_current\\\_replicas(service: str) -> int:
    try:
        dep = apps\\\_v1.read\\\_namespaced\\\_deployment(name=service, namespace=NAMESPACE)
        return dep.spec.replicas or 1
    except Exception as e:
        log.error(f"Failed to get replicas for {service}: {e}")
        return 1

def set\\\_replicas(service: str, target: int) -> bool:
    try:
        body = {"spec": {"replicas": target}}
        apps\\\_v1.patch\\\_namespaced\\\_deployment\\\_scale(
            name=service,
            namespace=NAMESPACE,
            body=body
        )
        log.info(f"\\\[SCALE] {service} → {target} replicas")
        return True
    except Exception as e:
        log.error(f"Failed to scale {service} to {target}: {e}")
        return False

def can\\\_scale(service: str) -> bool:
    last = last\\\_scale\\\_event.get(service)
    if last is None:
        return True
    return datetime.now() - last > timedelta(minutes=COOLDOWN\\\_MINUTES)

def record\\\_scale\\\_event(service: str):
    last\\\_scale\\\_event\\\[service] = datetime.now()

def log\\\_scale\\\_event(service: str, direction: str, old: int, new: int, reason: str):
    record = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "direction": direction,
        "old\\\_replicas": old,
        "new\\\_replicas": new,
        "reason": reason
    }
    log.info(f"\\\[EVENT] {json.dumps(record)}")
    # Append to experiment log file for later analysis
    log\\\_path = os.getenv("SCALE\\\_EVENT\\\_LOG", "scale\\\_events.jsonl")
    with open(log\\\_path, "a") as f:
        f.write(json.dumps(record) + "\\\\n")

# ── Bottleneck selector ──────────────────────────────────────────────────────
def select\\\_bottleneck\\\_service() -> str | None:
    """
    Select the service with the highest p95\\\_latency / SLO\\\_THRESHOLD ratio.
    Only considers services that have recent metrics and are not in cooldown.
    Falls back to front-end if no metrics available.
    """
    best\\\_service = None
    best\\\_score = 0.0

    for service in MONITORED\\\_SERVICES:
        if not can\\\_scale(service):
            continue
        metrics = recent\\\_metrics.get(service, \\\[])
        if not metrics:
            continue
        latest = metrics\\\[-1]
        p95 = latest.get("p95\\\_latency\\\_ms", 0.0)
        score = p95 / SLO\\\_THRESHOLD\\\_MS
        if score > best\\\_score:
            best\\\_score = score
            best\\\_service = service

    if best\\\_service is None:
        # Fallback: scale front-end if nothing else available and cooldown allows
        if can\\\_scale("front-end"):
            log.warning("No metric data for bottleneck selection, defaulting to front-end")
            return "front-end"
        return None

    return best\\\_service

# ── Scale-up handler ─────────────────────────────────────────────────────────
def handle\\\_scale\\\_up():
    service = select\\\_bottleneck\\\_service()
    if service is None:
        log.info("SCALE\\\_UP received but all services in cooldown or no metrics — skipped")
        return

    current = get\\\_current\\\_replicas(service)
    target = min(current + 1, MAX\\\_REPLICAS)

    if target == current:
        log.info(f"{service} already at MAX\\\_REPLICAS ({MAX\\\_REPLICAS}), skipping")
        return

    success = set\\\_replicas(service, target)
    if success:
        record\\\_scale\\\_event(service)
        log\\\_scale\\\_event(service, "SCALE\\\_UP", current, target,
                        reason="ML ensemble consensus")

# ── Scale-down policy ────────────────────────────────────────────────────────
def check\\\_scaledown():
    """
    Called every polling interval (30s).
    Scales down a service by 1 replica if ALL conditions hold for
    SCALEDOWN\\\_WINDOW consecutive intervals:
      - CPU utilization < SCALEDOWN\\\_CPU\\\_PCT
      - p95 latency < SCALEDOWN\\\_LAT\\\_RATIO × SLO\\\_THRESHOLD
      - current replicas > MIN\\\_REPLICAS
      - not in cooldown
    """
    for service in MONITORED\\\_SERVICES:
        if not can\\\_scale(service):
            continue

        history = recent\\\_metrics.get(service, \\\[])
        if len(history) < SCALEDOWN\\\_WINDOW:
            continue  # not enough history yet

        window = history\\\[-SCALEDOWN\\\_WINDOW:]
        cpu\\\_ok  = all(m.get("cpu\\\_pct", 100) < SCALEDOWN\\\_CPU\\\_PCT for m in window)
        lat\\\_ok  = all(
            m.get("p95\\\_latency\\\_ms", SLO\\\_THRESHOLD\\\_MS) < SCALEDOWN\\\_LAT\\\_RATIO \\\* SLO\\\_THRESHOLD\\\_MS
            for m in window
        )

        if not (cpu\\\_ok and lat\\\_ok):
            continue

        current = get\\\_current\\\_replicas(service)
        if current <= MIN\\\_REPLICAS:
            continue

        target = current - 1
        success = set\\\_replicas(service, target)
        if success:
            record\\\_scale\\\_event(service)
            log\\\_scale\\\_event(service, "SCALE\\\_DOWN", current, target,
                            reason=f"CPU<{SCALEDOWN\\\_CPU\\\_PCT}% and p95<{SCALEDOWN\\\_LAT\\\_RATIO}×SLO for {SCALEDOWN\\\_WINDOW} intervals")

# ── Metrics ingestion (side consumer) ───────────────────────────────────────
def ingest\\\_metric(msg\\\_value: dict):
    """
    Update rolling metrics window for a service.
    Expects msg\\\_value to contain: service, p95\\\_latency\\\_ms, cpu\\\_pct, mem\\\_usage, rps, etc.
    Adjust field names to match your actual Kafka metrics schema.
    """
    service = msg\\\_value.get("service")
    if service not in MONITORED\\\_SERVICES:
        return
    recent\\\_metrics\\\[service].append(msg\\\_value)
    # Keep only the last SCALEDOWN\\\_WINDOW + 5 entries
    if len(recent\\\_metrics\\\[service]) > SCALEDOWN\\\_WINDOW + 5:
        recent\\\_metrics\\\[service].pop(0)

# ── Main consumer loop ───────────────────────────────────────────────────────
def run():
    consumer = Consumer({
        "bootstrap.servers": KAFKA\\\_BOOTSTRAP,
        "group.id": "scaling-controller",
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    })
    consumer.subscribe(\\\[DECISIONS\\\_TOPIC, METRICS\\\_TOPIC])
    log.info(f"Scaling controller started. Subscribed to: {DECISIONS\\\_TOPIC}, {METRICS\\\_TOPIC}")

    last\\\_scaledown\\\_check = datetime.now()

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            # Run scale-down check every 30 seconds regardless of messages
            if datetime.now() - last\\\_scaledown\\\_check >= timedelta(seconds=30):
                check\\\_scaledown()
                last\\\_scaledown\\\_check = datetime.now()

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError.\\\_PARTITION\\\_EOF:
                    log.error(f"Kafka error: {msg.error()}")
                continue

            topic = msg.topic()
            try:
                value = json.loads(msg.value().decode("utf-8"))
            except Exception as e:
                log.warning(f"Failed to decode message: {e}")
                continue

            if topic == METRICS\\\_TOPIC:
                ingest\\\_metric(value)

            elif topic == DECISIONS\\\_TOPIC:
                decision = value.get("decision", "NO\\\_OP").upper()
                log.info(f"\\\[DECISION] Received: {decision}")
                if decision == "SCALE\\\_UP":
                    handle\\\_scale\\\_up()

    except KeyboardInterrupt:
        log.info("Shutting down scaling controller")
    finally:
        consumer.close()

if \\\_\\\_name\\\_\\\_ == "\\\_\\\_main\\\_\\\_":
    run()
```

**IMPORTANT — field name alignment:** The `ingest\\\_metric` function uses `p95\\\_latency\\\_ms`
and `cpu\\\_pct` as keys. Check your actual Kafka metrics schema and rename these to match
exactly. Do not rename anything in the K8s calls.

### 1.3 Deployment Manifest

Create `k8s/scaling-controller-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scaling-controller
  namespace: sock-shop
spec:
  replicas: 1
  selector:
    matchLabels:
      app: scaling-controller
  template:
    metadata:
      labels:
        app: scaling-controller
    spec:
      serviceAccountName: scaling-controller-sa
      containers:
      - name: controller
        image: gcr.io/YOUR\\\_PROJECT\\\_ID/scaling-controller:latest
        env:
        - name: NAMESPACE
          value: "sock-shop"
        - name: KAFKA\\\_BOOTSTRAP\\\_SERVERS
          value: "YOUR\\\_KAFKA\\\_BOOTSTRAP:9092"
        - name: SLO\\\_THRESHOLD\\\_MS
          value: "36.0"
        - name: SCALE\\\_EVENT\\\_LOG
          value: "/logs/scale\\\_events.jsonl"
        volumeMounts:
        - name: logs
          mountPath: /logs
      volumes:
      - name: logs
        emptyDir: {}
```

Replace `YOUR\\\_PROJECT\\\_ID` and `YOUR\\\_KAFKA\\\_BOOTSTRAP` before applying.

### 1.4 Smoke Test Verification

After deploying, run this to verify the controller can scale:

```bash
# Verify RBAC works — should return deployment info, not a 403
kubectl auth can-i patch deployments/scale --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop

# Manually trigger a scale event by publishing to the decisions topic
# (use your existing Kafka producer or kafkacat)
echo '{"decision": "SCALE\\\_UP", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' | \\\\
  kafkacat -P -b YOUR\\\_KAFKA\\\_BOOTSTRAP:9092 -t scaling-decisions

# Watch replicas change in real time
kubectl get pods -n sock-shop -w | grep -E "front-end|carts|orders"
```

The smoke test passes when you see a replica count increment in response to the manual
Kafka message. Do not proceed to experiments until this works.

\---

## Part 2 — Reactive HPA Baseline Configuration

Create `k8s/hpa-baseline.yaml`. This configures vanilla CPU-based HPA at 70% threshold
for all 7 monitored services — the standard baseline used in autoscaling literature.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: front-end-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: front-end
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: carts-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: carts
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orders-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orders
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: catalogue-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: catalogue
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: payment-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: shipping-hpa
  namespace: sock-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: shipping
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

**Switching between conditions:**

```bash
# Enable reactive baseline (Condition B)
kubectl apply -f k8s/hpa-baseline.yaml
# Also stop the scaling controller pod
kubectl scale deployment scaling-controller -n sock-shop --replicas=0

# Enable proactive system (Condition A)
kubectl delete -f k8s/hpa-baseline.yaml --ignore-not-found
# Also restart the scaling controller
kubectl scale deployment scaling-controller -n sock-shop --replicas=1
```

\---

## Part 3 — Experiment Runner

### 3.1 Run Configuration

Create `experiments/run\\\_config.py`:

```python
from dataclasses import dataclass

SLO\\\_THRESHOLD\\\_MS = 36.0
NAMESPACE        = "sock-shop"
POLL\\\_INTERVAL\\\_S  = 30

MONITORED\\\_SERVICES = \\\[
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

@dataclass
class ExperimentRun:
    condition: str    # "proactive" or "reactive"
    pattern:   str    # "constant", "step", "spike", "ramp"
    run\\\_id:    int    # 1-based

# Repetitions per pattern per condition:
# constant = 2 (steady-state, unlikely to produce scaling decisions)
# step, spike, ramp = 5 each
REPETITIONS = {
    "constant": 2,
    "step":     5,
    "spike":    5,
    "ramp":     5,
}

# Total: (2+5+5+5) × 2 conditions = 34 runs
# Duration per run: 12 min load + 3 min settle = 15 min
# Total experiment time: 34 × 15 = \\\~8.5 hours

def generate\\\_run\\\_schedule() -> list\\\[ExperimentRun]:
    """
    Alternates A/B per pattern to control for cluster drift.
    Order: proactive first, then reactive, for each pattern group.
    """
    schedule = \\\[]
    for pattern, reps in REPETITIONS.items():
        for i in range(1, reps + 1):
            schedule.append(ExperimentRun("proactive", pattern, i))
            schedule.append(ExperimentRun("reactive",  pattern, i))
    return schedule
```

### 3.2 Experiment Runner Script

Create `experiments/run\\\_experiments.py`:

```python
import subprocess
import time
import json
import os
import csv
from datetime import datetime
from pathlib import Path
from kubernetes import client, config
from run\\\_config import (
    ExperimentRun, MONITORED\\\_SERVICES, NAMESPACE,
    POLL\\\_INTERVAL\\\_S, SLO\\\_THRESHOLD\\\_MS, generate\\\_run\\\_schedule
)

config.load\\\_kube\\\_config()
apps\\\_v1  = client.AppsV1Api()
core\\\_v1  = client.CoreV1Api()

RESULTS\\\_DIR = Path("experiments/results")
RESULTS\\\_DIR.mkdir(parents=True, exist\\\_ok=True)

# ── Cluster control ──────────────────────────────────────────────────────────
def reset\\\_cluster():
    """Reset all monitored deployments to 1 replica."""
    print("  Resetting all deployments to 1 replica...")
    for svc in MONITORED\\\_SERVICES:
        try:
            apps\\\_v1.patch\\\_namespaced\\\_deployment\\\_scale(
                name=svc, namespace=NAMESPACE,
                body={"spec": {"replicas": 1}}
            )
        except Exception as e:
            print(f"  Warning: could not reset {svc}: {e}")
    time.sleep(120)  # 2 min for pods to stabilise
    print("  Cluster reset complete.")

def enable\\\_proactive():
    subprocess.run(
        \\\["kubectl", "delete", "-f", "k8s/hpa-baseline.yaml", "--ignore-not-found"],
        check=False, capture\\\_output=True
    )
    subprocess.run(
        \\\["kubectl", "scale", "deployment", "scaling-controller",
         "-n", NAMESPACE, "--replicas=1"],
        check=True
    )
    time.sleep(15)  # let controller come up
    print("  Proactive system active.")

def enable\\\_reactive():
    subprocess.run(
        \\\["kubectl", "scale", "deployment", "scaling-controller",
         "-n", NAMESPACE, "--replicas=0"],
        check=True
    )
    subprocess.run(
        \\\["kubectl", "apply", "-f", "k8s/hpa-baseline.yaml"],
        check=True
    )
    time.sleep(15)
    print("  Reactive HPA baseline active.")

# ── Metrics collection ───────────────────────────────────────────────────────
def collect\\\_snapshot(run: ExperimentRun, interval\\\_idx: int) -> dict:
    """
    Collect one polling snapshot for all services.
    Reads replica counts from K8s API.
    Reads latency/cpu metrics from YOUR existing metrics pipeline.

    TODO: Replace the placeholder metric reads below with calls to your
    actual metrics source (InfluxDB query, Prometheus query, or Kafka consumer).
    The field names must match what your pipeline produces.
    """
    snapshot = {
        "timestamp":    datetime.now().isoformat(),
        "run\\\_id":       run.run\\\_id,
        "condition":    run.condition,
        "pattern":      run.pattern,
        "interval\\\_idx": interval\\\_idx,
        "services":     {}
    }

    for svc in MONITORED\\\_SERVICES:
        try:
            dep = apps\\\_v1.read\\\_namespaced\\\_deployment(name=svc, namespace=NAMESPACE)
            replicas = dep.spec.replicas or 1
        except Exception:
            replicas = -1  # mark as unavailable

        # ── REPLACE THIS BLOCK with your real metrics query ──────────────
        # Example if using InfluxDB:
        #   result = influx\\\_client.query(f'SELECT last("p95") FROM "{svc}"')
        #   p95 = result\\\[0]\\\["last"]
        # Example if reading from your Kafka metrics cache:
        #   p95 = metrics\\\_cache\\\[svc].get("p95\\\_latency\\\_ms", 0.0)
        #   cpu = metrics\\\_cache\\\[svc].get("cpu\\\_pct", 0.0)
        p95 = 0.0  # REPLACE
        cpu = 0.0  # REPLACE
        # ─────────────────────────────────────────────────────────────────

        slo\\\_violated = p95 > SLO\\\_THRESHOLD\\\_MS
        snapshot\\\["services"]\\\[svc] = {
            "replicas":    replicas,
            "p95\\\_ms":      p95,
            "cpu\\\_pct":     cpu,
            "slo\\\_violated": slo\\\_violated,
        }

    return snapshot

# ── Single run ───────────────────────────────────────────────────────────────
def execute\\\_run(run: ExperimentRun) -> Path:
    label = f"{run.condition}\\\_{run.pattern}\\\_run{run.run\\\_id:02d}"
    print(f"\\\\n{'='\\\*60}")
    print(f"  RUN: {label}")
    print(f"{'='\\\*60}")

    # Switch condition
    if run.condition == "proactive":
        enable\\\_proactive()
    else:
        enable\\\_reactive()

    reset\\\_cluster()

    out\\\_path = RESULTS\\\_DIR / f"{label}.jsonl"
    snapshots = \\\[]

    # Start load generator
    # TODO: Replace with your actual Locust command / pattern flag
    load\\\_proc = subprocess.Popen(\\\[
        "python", "scripts/run\\\_load\\\_test.py",
        "--pattern", run.pattern
    ])

    print(f"  Load generator started (pattern={run.pattern}). Collecting metrics...")

    # Collect for 12 minutes = 24 intervals at 30s each
    n\\\_intervals = 24
    for i in range(n\\\_intervals):
        time.sleep(POLL\\\_INTERVAL\\\_S)
        snap = collect\\\_snapshot(run, i)
        snapshots.append(snap)

        # Live SLO violation indicator
        violations = \\\[
            svc for svc, m in snap\\\["services"].items()
            if m\\\["slo\\\_violated"]
        ]
        rep\\\_str = " ".join(
            f"{s}={snap\\\['services']\\\[s]\\\['replicas']}"
            for s in MONITORED\\\_SERVICES
        )
        print(f"  \\\[{i+1:02d}/{n\\\_intervals}] violations={violations or 'none'} | {rep\\\_str}")

    # Stop load generator
    load\\\_proc.terminate()
    load\\\_proc.wait()
    print("  Load generator stopped. Settling 3 minutes...")
    time.sleep(180)

    # Write results
    with open(out\\\_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\\\\n")

    print(f"  Results saved: {out\\\_path}")
    return out\\\_path

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    schedule = generate\\\_run\\\_schedule()
    total    = len(schedule)
    print(f"Starting experiment schedule: {total} runs")
    print(f"Estimated time: {total \\\* 15 / 60:.1f} hours\\\\n")

    completed = \\\[]
    for idx, run in enumerate(schedule, 1):
        print(f"\\\\nProgress: {idx}/{total}")
        try:
            out = execute\\\_run(run)
            completed.append({"run": run, "output": out, "status": "ok"})
        except Exception as e:
            print(f"  ERROR in run {run}: {e}")
            completed.append({"run": run, "output": None, "status": f"error: {e}"})

    print(f"\\\\n{'='\\\*60}")
    print(f"All runs complete. {sum(1 for c in completed if c\\\['status']=='ok')}/{total} succeeded.")
    print(f"Results in: {RESULTS\\\_DIR}")

if \\\_\\\_name\\\_\\\_ == "\\\_\\\_main\\\_\\\_":
    main()
```

\---

## Part 4 — Results Analyser

Create `experiments/analyse\\\_results.py`:

```python
"""
Reads all .jsonl result files from experiments/results/
Computes per-run summary metrics, then runs Mann-Whitney U tests
comparing proactive vs reactive per pattern.

Outputs:
  - experiments/results/summary.csv   (one row per run)
  - experiments/results/statistics.csv (Mann-Whitney results per metric × pattern)
  - Console table for copy-paste into paper
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
from scipy.stats import mannwhitneyu
import numpy as np

SLO\\\_THRESHOLD\\\_MS  = 36.0
RESULTS\\\_DIR       = Path("experiments/results")
MONITORED\\\_SERVICES = \\\[
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

# ── Per-run metrics ──────────────────────────────────────────────────────────
def summarise\\\_run(jsonl\\\_path: Path) -> dict:
    snapshots = \\\[]
    with open(jsonl\\\_path) as f:
        for line in f:
            snapshots.append(json.loads(line))

    if not snapshots:
        return {}

    # Parse metadata from filename: condition\\\_pattern\\\_runNN.jsonl
    stem = jsonl\\\_path.stem  # e.g. "proactive\\\_step\\\_run03"
    parts = stem.split("\\\_")
    condition = parts\\\[0]
    pattern   = parts\\\[1]
    run\\\_id    = int(parts\\\[2].replace("run", ""))

    n\\\_intervals = len(snapshots)

    # SLO violation rate: fraction of intervals where front-end p95 > SLO
    fe\\\_violations = sum(
        1 for s in snapshots
        if s\\\["services"]\\\["front-end"]\\\["slo\\\_violated"]
    )
    slo\\\_violation\\\_rate = fe\\\_violations / n\\\_intervals

    # Total replica-seconds across all services
    # Each interval = 30 seconds
    total\\\_replica\\\_seconds = sum(
        snap\\\["services"]\\\[svc]\\\["replicas"] \\\* 30
        for snap in snapshots
        for svc in MONITORED\\\_SERVICES
        if snap\\\["services"]\\\[svc]\\\["replicas"] > 0
    )

    # Number of scale-up events: count intervals where any service increased replicas
    scale\\\_up\\\_events = 0
    for i in range(1, n\\\_intervals):
        prev = snapshots\\\[i-1]
        curr = snapshots\\\[i]
        for svc in MONITORED\\\_SERVICES:
            if curr\\\["services"]\\\[svc]\\\["replicas"] > prev\\\["services"]\\\[svc]\\\["replicas"]:
                scale\\\_up\\\_events += 1

    # Time to SLO recovery (TTSR): avg intervals from violation start to recovery
    # Find violation runs (consecutive violated intervals), measure length
    fe = \\\[s\\\["services"]\\\["front-end"]\\\["slo\\\_violated"] for s in snapshots]
    ttsr\\\_values = \\\[]
    i = 0
    while i < len(fe):
        if fe\\\[i]:
            j = i
            while j < len(fe) and fe\\\[j]:
                j += 1
            ttsr\\\_values.append(j - i)  # length of violation streak in intervals
            i = j
        else:
            i += 1
    avg\\\_ttsr = np.mean(ttsr\\\_values) if ttsr\\\_values else 0.0

    # Peak replicas (max across all services and intervals)
    peak\\\_replicas = max(
        s\\\["services"]\\\[svc]\\\["replicas"]
        for s in snapshots
        for svc in MONITORED\\\_SERVICES
    )

    return {
        "condition":           condition,
        "pattern":             pattern,
        "run\\\_id":              run\\\_id,
        "slo\\\_violation\\\_rate":  round(slo\\\_violation\\\_rate, 4),
        "total\\\_replica\\\_sec":   round(total\\\_replica\\\_seconds, 1),
        "scale\\\_up\\\_events":     scale\\\_up\\\_events,
        "avg\\\_ttsr\\\_intervals":  round(avg\\\_ttsr, 2),
        "peak\\\_replicas":       peak\\\_replicas,
        "n\\\_intervals":         n\\\_intervals,
    }

# ── Statistical comparison ───────────────────────────────────────────────────
def rank\\\_biserial(u\\\_stat, n1, n2):
    """Effect size for Mann-Whitney U."""
    return 1 - (2 \\\* u\\\_stat) / (n1 \\\* n2)

def run\\\_statistics(summaries: list\\\[dict]) -> list\\\[dict]:
    metrics = \\\[
        "slo\\\_violation\\\_rate",
        "total\\\_replica\\\_sec",
        "scale\\\_up\\\_events",
        "avg\\\_ttsr\\\_intervals",
    ]
    patterns = \\\["constant", "step", "spike", "ramp"]
    results = \\\[]

    for pattern in patterns:
        for metric in metrics:
            pro = \\\[s\\\[metric] for s in summaries
                   if s\\\["condition"] == "proactive" and s\\\["pattern"] == pattern]
            rea = \\\[s\\\[metric] for s in summaries
                   if s\\\["condition"] == "reactive"  and s\\\["pattern"] == pattern]

            if len(pro) < 2 or len(rea) < 2:
                continue

            u\\\_stat, p\\\_val = mannwhitneyu(pro, rea, alternative="two-sided")
            r = rank\\\_biserial(u\\\_stat, len(pro), len(rea))

            results.append({
                "pattern":          pattern,
                "metric":           metric,
                "proactive\\\_median": round(float(np.median(pro)), 4),
                "proactive\\\_iqr":    round(float(np.percentile(pro, 75) - np.percentile(pro, 25)), 4),
                "reactive\\\_median":  round(float(np.median(rea)), 4),
                "reactive\\\_iqr":     round(float(np.percentile(rea, 75) - np.percentile(rea, 25)), 4),
                "u\\\_stat":           round(u\\\_stat, 2),
                "p\\\_value":          round(p\\\_val, 4),
                "effect\\\_size\\\_r":    round(r, 3),
                "significant":      p\\\_val < 0.05,
            })

    return results

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    result\\\_files = sorted(RESULTS\\\_DIR.glob("\\\*.jsonl"))
    if not result\\\_files:
        print(f"No result files found in {RESULTS\\\_DIR}")
        return

    print(f"Analysing {len(result\\\_files)} result files...")
    summaries = \\\[summarise\\\_run(f) for f in result\\\_files]
    summaries = \\\[s for s in summaries if s]  # filter empties

    # Write summary CSV
    summary\\\_path = RESULTS\\\_DIR / "summary.csv"
    with open(summary\\\_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=summaries\\\[0].keys())
        w.writeheader()
        w.writerows(summaries)
    print(f"Summary written: {summary\\\_path}")

    # Run statistics
    stats = run\\\_statistics(summaries)

    stats\\\_path = RESULTS\\\_DIR / "statistics.csv"
    with open(stats\\\_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=stats\\\[0].keys())
        w.writeheader()
        w.writerows(stats)
    print(f"Statistics written: {stats\\\_path}")

    # Console table
    print("\\\\n" + "="\\\*90)
    print("RESULTS TABLE (copy into paper)")
    print("="\\\*90)
    print(f"{'Pattern':<10} {'Metric':<22} {'Proactive':>20} {'Reactive':>20} {'p':>8} {'r':>8} {'sig':>5}")
    print("-"\\\*90)
    for r in stats:
        pro\\\_str = f"{r\\\['proactive\\\_median']} ± {r\\\['proactive\\\_iqr']}"
        rea\\\_str = f"{r\\\['reactive\\\_median']} ± {r\\\['reactive\\\_iqr']}"
        sig     = "✓" if r\\\["significant"] else ""
        print(f"{r\\\['pattern']:<10} {r\\\['metric']:<22} {pro\\\_str:>20} {rea\\\_str:>20} "
              f"{r\\\['p\\\_value']:>8.4f} {r\\\['effect\\\_size\\\_r']:>8.3f} {sig:>5}")

if \\\_\\\_name\\\_\\\_ == "\\\_\\\_main\\\_\\\_":
    main()
```

\---

## Execution Order

Execute **exactly in this sequence**. Do not skip steps.

### Step 1 — Deploy RBAC and scaling controller

```bash
kubectl apply -f k8s/scaling-controller-rbac.yaml
# Build and push scaling controller image, then:
kubectl apply -f k8s/scaling-controller-deployment.yaml
```

### Step 2 — Smoke test

```bash
# Verify RBAC
kubectl auth can-i patch deployments/scale \\\\
  --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop

# Send a manual SCALE\\\_UP and watch replicas
echo '{"decision":"SCALE\\\_UP"}' | kafkacat -P -b YOUR\\\_KAFKA:9092 -t scaling-decisions
kubectl get pods -n sock-shop -w
```

**Do not proceed past Step 2 until you see a replica increment.**

### Step 3 — Fill in the metrics TODO

In `run\\\_experiments.py`, replace the placeholder metric reads in `collect\\\_snapshot()`
with your actual metrics source. This is the only integration point left open.

### Step 4 — Run all experiments (start before sleeping)

```bash
cd experiments
python run\\\_experiments.py
```

This runs all 34 runs unattended (\~8.5 hours). Start it and let it run overnight.

### Step 5 — Analyse

```bash
python analyse\\\_results.py
```

Copy the console table output directly into the paper's results section.

\---

## Notes for the Agent

* **Do not change Kafka topic names** without confirming they match the existing
consumer configuration.
* **Do not rename K8s deployment names** — `front-end`, `carts`, etc. must match
exactly what is deployed in the `sock-shop` namespace.
* **The metrics TODO in `collect\\\_snapshot()` is intentional** — it must be filled in
by the developer since the metrics source (InfluxDB / Prometheus / Kafka cache)
is specific to their pipeline setup.
* **`confluent\\\_kafka` is the assumed Kafka client** — if the existing codebase uses
`kafka-python`, replace the Consumer import and configuration accordingly.
* **All file paths are relative to the project root.**
* Scaling controller requires `kubernetes` Python package: `pip install kubernetes`.
* Analyser requires `scipy` and `numpy`: `pip install scipy numpy`.

