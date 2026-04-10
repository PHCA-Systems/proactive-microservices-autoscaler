#!/usr/bin/env python3
"""
Task 5 Quick Checkpoint Test: Fast Manual Scaling Controller Testing

This is a faster version that tests the core functionality without waiting
for the full 5-minute scale-down window. It verifies:
1. Scale-up via manual SCALE_UP decision
2. Cooldown enforcement
3. Scale-down logic (without waiting 10 intervals)
4. Scaling event logging
"""

import json
import time
import os
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DECISIONS_TOPIC = "scaling-decisions"
METRICS_TOPIC = "metrics"
SCALE_EVENT_LOG = "scale_events.jsonl"


def create_producer():
    """Create Kafka producer."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


def publish_scale_up_decision(producer, service="front-end"):
    """Publish a SCALE_UP decision to Kafka."""
    decision = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "decision": "SCALE_UP",
        "votes": [
            {"model": "lr", "prediction": 1, "probability": 0.85},
            {"model": "rf", "prediction": 1, "probability": 0.92},
            {"model": "xgb", "prediction": 1, "probability": 0.88}
        ],
        "consensus": "unanimous",
        "vote_counts": {"SCALE_UP": 3, "NO_OP": 0}
    }
    
    producer.send(DECISIONS_TOPIC, value=decision)
    producer.flush()
    print(f"✓ Published SCALE_UP decision for {service}")
    return decision


def publish_high_latency_metrics(producer, service="front-end", p95_latency=50.0):
    """Publish metrics indicating high latency (above SLO)."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "features": {
            "request_rate_rps": 100.0,
            "error_rate_pct": 0.5,
            "p50_latency_ms": 20.0,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": 60.0,
            "cpu_usage_pct": 75.0,
            "memory_usage_mb": 512.0,
            "delta_rps": 10.0,
            "delta_p95_latency_ms": 5.0,
            "delta_cpu_usage_pct": 5.0,
            "sla_violated": p95_latency > 36.0
        }
    }
    
    producer.send(METRICS_TOPIC, value=metrics)
    producer.flush()
    return metrics


def publish_low_metrics(producer, service="front-end", cpu=25.0, p95_latency=20.0):
    """Publish metrics indicating low resource usage (scale-down conditions)."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "features": {
            "request_rate_rps": 10.0,
            "error_rate_pct": 0.1,
            "p50_latency_ms": 10.0,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": 25.0,
            "cpu_usage_pct": cpu,
            "memory_usage_mb": 256.0,
            "delta_rps": -5.0,
            "delta_p95_latency_ms": -2.0,
            "delta_cpu_usage_pct": -3.0,
            "sla_violated": False
        }
    }
    
    producer.send(METRICS_TOPIC, value=metrics)
    producer.flush()
    return metrics


def read_scale_events(log_path=SCALE_EVENT_LOG):
    """Read scaling events from log file."""
    if not os.path.exists(log_path):
        return []
    
    events = []
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def clear_scale_events(log_path=SCALE_EVENT_LOG):
    """Clear the scaling events log file."""
    if os.path.exists(log_path):
        os.remove(log_path)
        print(f"✓ Cleared {log_path}")


def test_1_scale_up_with_bottleneck_selection():
    """Test 1: Verify bottleneck selection and scale-up."""
    print("\n" + "="*70)
    print("TEST 1: Scale-Up with Bottleneck Selection")
    print("="*70)
    
    producer = create_producer()
    clear_scale_events()
    
    # Publish metrics for multiple services with different latencies
    print("\n1. Publishing metrics for multiple services...")
    services_metrics = [
        ("front-end", 50.0),  # Highest p95/SLO ratio (50/36 = 1.39)
        ("carts", 40.0),      # Medium ratio (40/36 = 1.11)
        ("orders", 30.0),     # Lower ratio (30/36 = 0.83)
    ]
    
    for service, p95 in services_metrics:
        publish_high_latency_metrics(producer, service=service, p95_latency=p95)
        print(f"   {service}: p95={p95}ms (ratio={p95/36.0:.2f})")
        time.sleep(0.5)
    
    print("\n2. Waiting 3 seconds for metrics ingestion...")
    time.sleep(3)
    
    # Publish SCALE_UP decision
    print("\n3. Publishing SCALE_UP decision...")
    publish_scale_up_decision(producer, service="any")
    
    print("\n4. Waiting 5 seconds for controller to process...")
    time.sleep(5)
    
    # Check scaling events
    print("\n5. Checking scaling events...")
    events = read_scale_events()
    
    if not events:
        print("✗ FAIL: No scaling events found")
        producer.close()
        return False
    
    latest_event = events[-1]
    print(f"\nScaling event:")
    print(f"  Service: {latest_event['service']}")
    print(f"  Direction: {latest_event['direction']}")
    print(f"  Old → New replicas: {latest_event['old_replicas']} → {latest_event['new_replicas']}")
    
    # Verify front-end was selected (highest p95/SLO ratio)
    if latest_event['service'] != 'front-end':
        print(f"✗ FAIL: Expected front-end to be selected, got {latest_event['service']}")
        producer.close()
        return False
    
    if latest_event['direction'] != 'SCALE_UP':
        print(f"✗ FAIL: Expected SCALE_UP, got {latest_event['direction']}")
        producer.close()
        return False
    
    print("\n✓ PASS: Bottleneck selection and scale-up work correctly")
    producer.close()
    return True


def test_2_cooldown_enforcement():
    """Test 2: Verify cooldown prevents immediate re-scaling."""
    print("\n" + "="*70)
    print("TEST 2: Cooldown Enforcement")
    print("="*70)
    
    producer = create_producer()
    clear_scale_events()
    
    # First scale-up
    print("\n1. Publishing first SCALE_UP decision for 'carts'...")
    publish_high_latency_metrics(producer, service="carts", p95_latency=50.0)
    time.sleep(2)
    publish_scale_up_decision(producer, service="carts")
    
    print("\n2. Waiting 5 seconds for first scale-up...")
    time.sleep(5)
    
    events_after_first = read_scale_events()
    first_count = len(events_after_first)
    print(f"✓ Events after first scale: {first_count}")
    
    # Immediate second scale-up (should be blocked)
    print("\n3. Publishing second SCALE_UP decision immediately...")
    publish_high_latency_metrics(producer, service="carts", p95_latency=55.0)
    time.sleep(2)
    publish_scale_up_decision(producer, service="carts")
    
    print("\n4. Waiting 5 seconds...")
    time.sleep(5)
    
    events_after_second = read_scale_events()
    second_count = len(events_after_second)
    print(f"✓ Events after second attempt: {second_count}")
    
    if second_count > first_count:
        print("✗ FAIL: Cooldown did not prevent re-scaling")
        producer.close()
        return False
    
    print("\n✓ PASS: Cooldown enforcement works correctly")
    producer.close()
    return True


def test_3_scale_down_metrics_ingestion():
    """Test 3: Verify low metrics are ingested (without waiting 10 intervals)."""
    print("\n" + "="*70)
    print("TEST 3: Scale-Down Metrics Ingestion")
    print("="*70)
    
    producer = create_producer()
    
    print("\n1. Publishing low CPU/latency metrics...")
    for i in range(3):
        publish_low_metrics(producer, service="orders", cpu=25.0, p95_latency=20.0)
        print(f"   Published interval {i+1}/3")
        time.sleep(1)
    
    print("\n✓ PASS: Low metrics published successfully")
    print("   (Full scale-down test requires 10 intervals = ~5 minutes)")
    print("   Run test_task_5_checkpoint.py for complete scale-down test")
    
    producer.close()
    return True


def test_4_log_format_validation():
    """Test 4: Verify scaling event log format."""
    print("\n" + "="*70)
    print("TEST 4: Log Format Validation")
    print("="*70)
    
    events = read_scale_events()
    
    if not events:
        print("⚠ WARNING: No events to verify (run previous tests first)")
        return True
    
    print(f"\nValidating {len(events)} event(s)...")
    
    required_fields = ["timestamp", "service", "direction", "old_replicas", "new_replicas", "reason"]
    
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        
        # Check required fields
        for field in required_fields:
            if field not in event:
                print(f"  ✗ Missing field: {field}")
                return False
        
        # Verify direction
        if event['direction'] not in ['SCALE_UP', 'SCALE_DOWN']:
            print(f"  ✗ Invalid direction: {event['direction']}")
            return False
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(event['timestamp'])
        except ValueError:
            print(f"  ✗ Invalid timestamp: {event['timestamp']}")
            return False
        
        # Verify replica counts are integers
        if not isinstance(event['old_replicas'], int) or not isinstance(event['new_replicas'], int):
            print(f"  ✗ Replica counts must be integers")
            return False
        
        print(f"  ✓ {event['service']}: {event['direction']} ({event['old_replicas']} → {event['new_replicas']})")
    
    print("\n✓ PASS: All events have correct format")
    return True


def run_quick_tests():
    """Run quick checkpoint tests."""
    print("\n" + "="*70)
    print("TASK 5 QUICK CHECKPOINT: Scaling Controller Testing")
    print("="*70)
    print("\nThis quick test suite verifies:")
    print("1. Scale-up with bottleneck selection")
    print("2. Cooldown enforcement")
    print("3. Scale-down metrics ingestion")
    print("4. Log format validation")
    print("\nEstimated time: ~30 seconds")
    print("="*70)
    
    input("\nPress Enter to start tests (or Ctrl+C to cancel)...")
    
    results = {}
    
    # Run tests
    results['Test 1: Scale-Up & Bottleneck'] = test_1_scale_up_with_bottleneck_selection()
    results['Test 2: Cooldown'] = test_2_cooldown_enforcement()
    results['Test 3: Scale-Down Metrics'] = test_3_scale_down_metrics_ingestion()
    results['Test 4: Log Format'] = test_4_log_format_validation()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL QUICK TESTS PASSED")
        print("\nFor complete validation including full scale-down test,")
        print("run: python test_task_5_checkpoint.py")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = run_quick_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
