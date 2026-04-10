#!/usr/bin/env python3
"""
Task 5 Checkpoint Test: Manual Scaling Controller Testing

This test script manually triggers scaling actions and verifies the controller
responds correctly. It tests:
1. Scale-up via manual SCALE_UP decision
2. Cooldown enforcement
3. Scale-down after 10 intervals of low metrics
4. Scaling event logging
"""

import json
import time
import os
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DECISIONS_TOPIC = "scaling-decisions"
METRICS_TOPIC = "metrics"
SCALE_EVENT_LOG = "scale_events.jsonl"

# Test services
TEST_SERVICES = ["front-end", "carts", "orders"]


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


def test_1_scale_up_decision():
    """Test 1: Manually publish SCALE_UP decision and verify replica increase."""
    print("\n" + "="*70)
    print("TEST 1: Scale-Up Decision")
    print("="*70)
    
    producer = create_producer()
    
    # First, publish high latency metrics for front-end to make it the bottleneck
    print("\n1. Publishing high latency metrics for front-end...")
    for i in range(3):
        publish_high_latency_metrics(producer, service="front-end", p95_latency=50.0)
        time.sleep(0.5)
    
    # Publish lower latency for other services
    for service in ["carts", "orders"]:
        publish_high_latency_metrics(producer, service=service, p95_latency=30.0)
        time.sleep(0.5)
    
    print("✓ Published metrics (front-end has highest p95/SLO ratio)")
    
    # Wait for metrics to be ingested
    print("\n2. Waiting 3 seconds for metrics ingestion...")
    time.sleep(3)
    
    # Clear previous events
    clear_scale_events()
    
    # Publish SCALE_UP decision
    print("\n3. Publishing SCALE_UP decision...")
    decision = publish_scale_up_decision(producer, service="front-end")
    
    # Wait for controller to process
    print("\n4. Waiting 5 seconds for controller to process...")
    time.sleep(5)
    
    # Check scaling events
    print("\n5. Checking scaling events log...")
    events = read_scale_events()
    
    if not events:
        print("✗ FAIL: No scaling events found in log")
        return False
    
    print(f"✓ Found {len(events)} scaling event(s)")
    
    # Verify the event
    latest_event = events[-1]
    print(f"\nLatest event:")
    print(f"  Service: {latest_event['service']}")
    print(f"  Direction: {latest_event['direction']}")
    print(f"  Old replicas: {latest_event['old_replicas']}")
    print(f"  New replicas: {latest_event['new_replicas']}")
    print(f"  Reason: {latest_event['reason']}")
    
    if latest_event['direction'] != 'SCALE_UP':
        print(f"✗ FAIL: Expected SCALE_UP, got {latest_event['direction']}")
        return False
    
    if latest_event['new_replicas'] != latest_event['old_replicas'] + 1:
        print(f"✗ FAIL: Replicas should increase by 1")
        return False
    
    print("\n✓ PASS: Scale-up executed correctly")
    producer.close()
    return True


def test_2_cooldown_enforcement():
    """Test 2: Verify cooldown prevents immediate re-scaling."""
    print("\n" + "="*70)
    print("TEST 2: Cooldown Enforcement")
    print("="*70)
    
    producer = create_producer()
    
    # Clear previous events
    clear_scale_events()
    
    # Publish first SCALE_UP decision
    print("\n1. Publishing first SCALE_UP decision...")
    publish_high_latency_metrics(producer, service="carts", p95_latency=50.0)
    time.sleep(2)
    publish_scale_up_decision(producer, service="carts")
    
    print("\n2. Waiting 5 seconds for first scale-up...")
    time.sleep(5)
    
    events_after_first = read_scale_events()
    first_event_count = len(events_after_first)
    print(f"✓ First scale-up completed ({first_event_count} events)")
    
    # Immediately publish second SCALE_UP decision (should be blocked by cooldown)
    print("\n3. Publishing second SCALE_UP decision immediately...")
    publish_high_latency_metrics(producer, service="carts", p95_latency=55.0)
    time.sleep(2)
    publish_scale_up_decision(producer, service="carts")
    
    print("\n4. Waiting 5 seconds...")
    time.sleep(5)
    
    events_after_second = read_scale_events()
    second_event_count = len(events_after_second)
    
    print(f"\nEvent count after first scale: {first_event_count}")
    print(f"Event count after second scale attempt: {second_event_count}")
    
    if second_event_count > first_event_count:
        print("✗ FAIL: Second scale-up was not blocked by cooldown")
        return False
    
    print("\n✓ PASS: Cooldown prevented immediate re-scaling")
    producer.close()
    return True


def test_3_scale_down_after_10_intervals():
    """Test 3: Inject low CPU/latency metrics and verify scale-down after 10 intervals."""
    print("\n" + "="*70)
    print("TEST 3: Scale-Down After 10 Intervals")
    print("="*70)
    
    producer = create_producer()
    
    # First, ensure the service has more than 1 replica by scaling up
    print("\n1. Scaling up 'orders' service first...")
    clear_scale_events()
    publish_high_latency_metrics(producer, service="orders", p95_latency=50.0)
    time.sleep(2)
    publish_scale_up_decision(producer, service="orders")
    time.sleep(5)
    
    initial_events = read_scale_events()
    print(f"✓ Initial scale-up completed ({len(initial_events)} events)")
    
    # Now inject low metrics for 10+ intervals
    print("\n2. Injecting low CPU/latency metrics for 10+ intervals...")
    print("   (This will take ~5 minutes due to 30-second intervals)")
    
    # Publish 12 intervals of low metrics (to be safe)
    for i in range(12):
        publish_low_metrics(producer, service="orders", cpu=25.0, p95_latency=20.0)
        print(f"   Interval {i+1}/12 published", end="\r")
        time.sleep(30)  # Wait 30 seconds between intervals
    
    print("\n\n3. Waiting additional 10 seconds for scale-down processing...")
    time.sleep(10)
    
    # Check for scale-down event
    print("\n4. Checking for scale-down event...")
    final_events = read_scale_events()
    
    scale_down_events = [e for e in final_events if e['direction'] == 'SCALE_DOWN']
    
    if not scale_down_events:
        print("✗ FAIL: No scale-down event found after 10 intervals of low metrics")
        print(f"Total events: {len(final_events)}")
        for event in final_events:
            print(f"  - {event['direction']} for {event['service']}")
        return False
    
    print(f"✓ Found {len(scale_down_events)} scale-down event(s)")
    
    latest_scale_down = scale_down_events[-1]
    print(f"\nLatest scale-down event:")
    print(f"  Service: {latest_scale_down['service']}")
    print(f"  Old replicas: {latest_scale_down['old_replicas']}")
    print(f"  New replicas: {latest_scale_down['new_replicas']}")
    print(f"  Reason: {latest_scale_down['reason']}")
    
    if latest_scale_down['new_replicas'] != latest_scale_down['old_replicas'] - 1:
        print(f"✗ FAIL: Replicas should decrease by 1")
        return False
    
    print("\n✓ PASS: Scale-down executed after 10 intervals")
    producer.close()
    return True


def test_4_verify_log_format():
    """Test 4: Verify scaling event log format."""
    print("\n" + "="*70)
    print("TEST 4: Verify Log Format")
    print("="*70)
    
    events = read_scale_events()
    
    if not events:
        print("✗ FAIL: No events to verify")
        return False
    
    print(f"\nVerifying format of {len(events)} event(s)...")
    
    required_fields = ["timestamp", "service", "direction", "old_replicas", "new_replicas", "reason"]
    
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        for field in required_fields:
            if field not in event:
                print(f"  ✗ Missing field: {field}")
                return False
            print(f"  ✓ {field}: {event[field]}")
        
        # Verify direction is valid
        if event['direction'] not in ['SCALE_UP', 'SCALE_DOWN']:
            print(f"  ✗ Invalid direction: {event['direction']}")
            return False
        
        # Verify timestamp is ISO 8601
        try:
            datetime.fromisoformat(event['timestamp'])
        except ValueError:
            print(f"  ✗ Invalid timestamp format: {event['timestamp']}")
            return False
    
    print("\n✓ PASS: All events have correct format")
    return True


def run_all_tests():
    """Run all checkpoint tests."""
    print("\n" + "="*70)
    print("TASK 5 CHECKPOINT: Scaling Controller Manual Testing")
    print("="*70)
    print("\nThis test suite will:")
    print("1. Manually publish SCALE_UP decisions")
    print("2. Verify cooldown enforcement")
    print("3. Test scale-down after 10 intervals (~5 minutes)")
    print("4. Verify scaling event log format")
    print("\nNOTE: Test 3 will take approximately 6-7 minutes to complete.")
    print("="*70)
    
    input("\nPress Enter to start tests (or Ctrl+C to cancel)...")
    
    results = {}
    
    # Run tests
    results['test_1'] = test_1_scale_up_decision()
    results['test_2'] = test_2_cooldown_enforcement()
    results['test_3'] = test_3_scale_down_after_10_intervals()
    results['test_4'] = test_4_verify_log_format()
    
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
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
