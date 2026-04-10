#!/usr/bin/env python3
"""
Scaling Controller
Executes scaling decisions by calling Kubernetes API
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# Configuration
NAMESPACE = os.getenv("NAMESPACE", "sock-shop")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
DECISIONS_TOPIC = os.getenv("DECISIONS_TOPIC", "scaling-decisions")
METRICS_TOPIC = os.getenv("METRICS_TOPIC", "metrics")
SLO_THRESHOLD_MS = float(os.getenv("SLO_THRESHOLD_MS", "36.0"))
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", "5"))
MIN_REPLICAS = int(os.getenv("MIN_REPLICAS", "1"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "10"))
SCALEDOWN_CPU_PCT = float(os.getenv("SCALEDOWN_CPU_PCT", "30.0"))
SCALEDOWN_LAT_RATIO = float(os.getenv("SCALEDOWN_LAT_RATIO", "0.7"))
SCALEDOWN_WINDOW = int(os.getenv("SCALEDOWN_WINDOW", "10"))

MONITORED_SERVICES = [
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

# State
last_scale_event = {}
recent_metrics = {s: [] for s in MONITORED_SERVICES}


def init_k8s():
    """Initialize Kubernetes client."""
    try:
        config.load_incluster_config()
        log.info("Loaded in-cluster K8s config")
    except Exception:
        config.load_kube_config()
        log.info("Loaded local kubeconfig")
    return client.AppsV1Api()


def get_current_replicas(apps_v1, service: str) -> int:
    """Get current replica count for a service."""
    try:
        dep = apps_v1.read_namespaced_deployment(name=service, namespace=NAMESPACE)
        return dep.spec.replicas or 1
    except ApiException as e:
        log.error(f"Failed to get replicas for {service}: {e}")
        return 1


def set_replicas(apps_v1, service: str, target: int) -> bool:
    """Set replica count for a service."""
    try:
        body = {"spec": {"replicas": target}}
        apps_v1.patch_namespaced_deployment_scale(
            name=service,
            namespace=NAMESPACE,
            body=body
        )
        log.info(f"[SCALE] {service} → {target} replicas")
        return True
    except ApiException as e:
        log.error(f"Failed to scale {service} to {target}: {e}")
        return False


def can_scale(service: str) -> bool:
    """Check if service is not in cooldown period."""
    last = last_scale_event.get(service)
    if last is None:
        return True
    return datetime.now() - last > timedelta(minutes=COOLDOWN_MINUTES)


def record_scale_event(service: str):
    """Record that a scale event occurred."""
    last_scale_event[service] = datetime.now()


def log_scale_event(service: str, direction: str, old: int, new: int, reason: str):
    """Log scaling event to file."""
    record = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "direction": direction,
        "old_replicas": old,
        "new_replicas": new,
        "reason": reason
    }
    log.info(f"[EVENT] {json.dumps(record)}")
    
    log_path = os.getenv("SCALE_EVENT_LOG", "scale_events.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def select_bottleneck_service() -> str | None:
    """
    Select service with highest p95_latency / SLO_THRESHOLD ratio.
    Falls back to front-end if no metrics available.
    """
    best_service = None
    best_score = 0.0

    for service in MONITORED_SERVICES:
        if not can_scale(service):
            continue
        metrics = recent_metrics.get(service, [])
        if not metrics:
            continue
        latest = metrics[-1]
        p95 = latest.get("p95_latency_ms", 0.0)
        score = p95 / SLO_THRESHOLD_MS
        if score > best_score:
            best_score = score
            best_service = service

    if best_service is None:
        if can_scale("front-end"):
            log.warning("No metric data for bottleneck selection, defaulting to front-end")
            return "front-end"
        return None

    return best_service


def handle_scale_up(apps_v1, service: str):
    """Handle scale-up decision."""
    if not can_scale(service):
        log.info(f"SCALE_UP for {service} skipped - in cooldown")
        return

    current = get_current_replicas(apps_v1, service)
    target = min(current + 1, MAX_REPLICAS)

    if target == current:
        log.info(f"{service} already at MAX_REPLICAS ({MAX_REPLICAS}), skipping")
        return

    success = set_replicas(apps_v1, service, target)
    if success:
        record_scale_event(service)
        log_scale_event(service, "SCALE_UP", current, target,
                       reason="ML ensemble consensus")


def check_scaledown(apps_v1):
    """
    Check if any service should be scaled down.
    Scales down by 1 replica if ALL conditions hold for SCALEDOWN_WINDOW intervals:
    - CPU < SCALEDOWN_CPU_PCT
    - p95 latency < SCALEDOWN_LAT_RATIO × SLO_THRESHOLD
    - current replicas > MIN_REPLICAS
    - not in cooldown
    """
    for service in MONITORED_SERVICES:
        if not can_scale(service):
            continue

        history = recent_metrics.get(service, [])
        if len(history) < SCALEDOWN_WINDOW:
            continue

        window = history[-SCALEDOWN_WINDOW:]
        cpu_ok = all(m.get("cpu_usage_pct", 100) < SCALEDOWN_CPU_PCT for m in window)
        lat_ok = all(
            m.get("p95_latency_ms", SLO_THRESHOLD_MS) < SCALEDOWN_LAT_RATIO * SLO_THRESHOLD_MS
            for m in window
        )

        if not (cpu_ok and lat_ok):
            continue

        current = get_current_replicas(apps_v1, service)
        if current <= MIN_REPLICAS:
            continue

        target = current - 1
        success = set_replicas(apps_v1, service, target)
        if success:
            record_scale_event(service)
            log_scale_event(service, "SCALE_DOWN", current, target,
                           reason=f"CPU<{SCALEDOWN_CPU_PCT}% and p95<{SCALEDOWN_LAT_RATIO}×SLO for {SCALEDOWN_WINDOW} intervals")


def ingest_metric(msg_value: dict):
    """Update rolling metrics window for a service."""
    service = msg_value.get("service")
    if service not in MONITORED_SERVICES:
        return
    
    # Flatten the nested structure if needed
    if "features" in msg_value:
        # Merge features into the main dict for easier access
        flattened = {
            "service": service,
            "timestamp": msg_value.get("timestamp"),
            **msg_value["features"]
        }
        recent_metrics[service].append(flattened)
    else:
        recent_metrics[service].append(msg_value)
    
    # Keep only the most recent metrics
    if len(recent_metrics[service]) > SCALEDOWN_WINDOW + 5:
        recent_metrics[service].pop(0)


def run():
    """Main controller loop."""
    apps_v1 = init_k8s()
    
    # Connect to Kafka
    log.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
    consumer = KafkaConsumer(
        DECISIONS_TOPIC,
        METRICS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='scaling-controller',
        consumer_timeout_ms=1000
    )
    
    log.info(f"Scaling controller started. Subscribed to: {DECISIONS_TOPIC}, {METRICS_TOPIC}")

    last_scaledown_check = datetime.now()

    try:
        while True:
            # Run scale-down check every 30 seconds
            if datetime.now() - last_scaledown_check >= timedelta(seconds=30):
                check_scaledown(apps_v1)
                last_scaledown_check = datetime.now()

            # Poll for messages
            messages = consumer.poll(timeout_ms=1000)
            
            for topic_partition, records in messages.items():
                for message in records:
                    topic = message.topic
                    value = message.value

                    if topic == METRICS_TOPIC:
                        ingest_metric(value)

                    elif topic == DECISIONS_TOPIC:
                        decision = value.get("decision", "NO ACTION").upper()
                        service = value.get("service", "unknown")
                        
                        log.info(f"[DECISION] Received: {decision} for {service}")
                        
                        if "SCALE UP" in decision or "SCALE_UP" in decision:
                            # Select bottleneck service (highest p95/SLO ratio)
                            bottleneck = select_bottleneck_service()
                            if bottleneck:
                                log.info(f"[BOTTLENECK] Selected {bottleneck} for scale-up")
                                handle_scale_up(apps_v1, bottleneck)
                            else:
                                log.warning("[BOTTLENECK] No service available for scale-up (all in cooldown)")

            time.sleep(0.1)

    except KeyboardInterrupt:
        log.info("Shutting down scaling controller")
    finally:
        consumer.close()


if __name__ == "__main__":
    run()
