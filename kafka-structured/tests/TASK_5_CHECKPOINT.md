# Task 5 Checkpoint: Scaling Controller Manual Testing

## Overview

This checkpoint validates that the scaling controller (Tasks 4.1-4.5) works correctly before proceeding to Phase 5. The tests manually trigger scaling actions and verify the controller responds as expected.

## Test Coverage

### Quick Tests (~30 seconds)
1. **Scale-Up with Bottleneck Selection**: Publishes metrics for multiple services and verifies the service with the highest p95/SLO ratio is scaled up
2. **Cooldown Enforcement**: Verifies that a second scale-up is blocked within the 5-minute cooldown period
3. **Scale-Down Metrics Ingestion**: Verifies low CPU/latency metrics are ingested correctly
4. **Log Format Validation**: Verifies scaling events are logged with correct format

### Full Checkpoint Tests (~7 minutes)
Includes all quick tests plus:
- **Scale-Down After 10 Intervals**: Injects low metrics for 10 consecutive 30-second intervals and verifies scale-down occurs

## Prerequisites

1. **Kafka Running**: Ensure Kafka broker is running and accessible
   ```bash
   # Check if Kafka is running
   docker ps | grep kafka
   ```

2. **Scaling Controller Running**: The controller must be running to process decisions
   ```bash
   cd kafka-structured/services/scaling-controller
   python controller.py
   ```

3. **Virtual Environment**: Tests use the existing venv
   ```bash
   # Should exist at:
   kafka-structured/services/metrics-aggregator/venv/
   ```

4. **Environment Variables** (optional):
   ```bash
   export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
   export SCALE_EVENT_LOG="scale_events.jsonl"
   ```

## Running the Tests

### Option 1: Using PowerShell Script (Recommended)

```powershell
cd kafka-structured/tests
./run_task_5_tests.ps1
```

The script will:
- Activate the virtual environment
- Check Kafka connection
- Prompt you to confirm the scaling controller is running
- Let you choose which tests to run

### Option 2: Manual Execution

#### Quick Tests
```bash
cd kafka-structured/tests
source ../services/metrics-aggregator/venv/bin/activate  # Linux/Mac
# or
../services/metrics-aggregator/venv/Scripts/activate     # Windows

python test_task_5_quick.py
```

#### Full Checkpoint Tests
```bash
python test_task_5_checkpoint.py
```

## Test Details

### Test 1: Scale-Up with Bottleneck Selection

**What it does:**
- Publishes metrics for 3 services with different p95 latencies:
  - front-end: 50ms (ratio 1.39)
  - carts: 40ms (ratio 1.11)
  - orders: 30ms (ratio 0.83)
- Publishes a SCALE_UP decision
- Verifies front-end (highest ratio) is scaled up

**Expected outcome:**
- Scaling event logged for front-end
- Direction: SCALE_UP
- Replicas increased by 1

### Test 2: Cooldown Enforcement

**What it does:**
- Publishes first SCALE_UP decision for 'carts'
- Waits for scale-up to complete
- Immediately publishes second SCALE_UP decision
- Verifies second scale-up is blocked

**Expected outcome:**
- First scale-up succeeds
- Second scale-up is blocked (no new event)
- Controller logs "in cooldown" message

### Test 3: Scale-Down Metrics Ingestion (Quick)

**What it does:**
- Publishes 3 intervals of low CPU (25%) and low latency (20ms) metrics
- Verifies metrics are published successfully

**Expected outcome:**
- Metrics published without errors
- Note: Full scale-down requires 10 intervals (~5 minutes)

### Test 3: Scale-Down After 10 Intervals (Full)

**What it does:**
- Scales up 'orders' service first (to have >1 replica)
- Publishes 12 intervals of low metrics (30 seconds apart)
- Waits for scale-down to occur

**Expected outcome:**
- Scale-down event logged after 10 intervals
- Direction: SCALE_DOWN
- Replicas decreased by 1
- Reason mentions CPU and latency thresholds

**Duration:** ~6-7 minutes (12 intervals × 30 seconds + processing time)

### Test 4: Log Format Validation

**What it does:**
- Reads all scaling events from log file
- Verifies each event has required fields
- Validates field types and values

**Expected outcome:**
- All events have: timestamp, service, direction, old_replicas, new_replicas, reason
- Timestamps are valid ISO 8601 format
- Direction is either SCALE_UP or SCALE_DOWN
- Replica counts are integers

## Interpreting Results

### Success Output
```
======================================================================
TEST SUMMARY
======================================================================
Test 1: Scale-Up & Bottleneck: ✓ PASS
Test 2: Cooldown: ✓ PASS
Test 3: Scale-Down Metrics: ✓ PASS
Test 4: Log Format: ✓ PASS

======================================================================
✓ ALL QUICK TESTS PASSED
======================================================================
```

### Failure Scenarios

#### No Scaling Events Found
**Symptom:** "✗ FAIL: No scaling events found"

**Possible causes:**
- Scaling controller not running
- Kafka connection issues
- Controller not subscribed to correct topics

**Solution:**
1. Check controller logs for errors
2. Verify Kafka topics exist: `kafka-topics --list`
3. Verify controller is consuming from `scaling-decisions` and `metrics` topics

#### Wrong Service Scaled
**Symptom:** "✗ FAIL: Expected front-end to be selected, got carts"

**Possible causes:**
- Bottleneck selection logic incorrect
- Metrics not ingested before decision

**Solution:**
1. Check controller logs for bottleneck selection
2. Verify metrics are published before decision
3. Review `select_bottleneck_service()` logic

#### Cooldown Not Enforced
**Symptom:** "✗ FAIL: Cooldown did not prevent re-scaling"

**Possible causes:**
- Cooldown tracking not working
- `can_scale()` logic incorrect

**Solution:**
1. Check controller logs for cooldown messages
2. Verify `last_scale_event` dictionary is updated
3. Review cooldown period configuration (default 5 minutes)

#### Scale-Down Not Triggered
**Symptom:** "✗ FAIL: No scale-down event found after 10 intervals"

**Possible causes:**
- Metrics not ingested correctly
- Scale-down window not filled
- Service already at MIN_REPLICAS

**Solution:**
1. Check controller logs for scale-down evaluation
2. Verify metrics are consumed from `metrics` topic
3. Ensure service has >1 replica before test
4. Review `check_scaledown()` logic

## Log Files

### Scaling Events Log
**Location:** `kafka-structured/tests/scale_events.jsonl`

**Format:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "service": "front-end",
  "direction": "SCALE_UP",
  "old_replicas": 1,
  "new_replicas": 2,
  "reason": "ML ensemble consensus"
}
```

### Controller Logs
Check the scaling controller terminal output for:
- `[DECISION] Received: SCALE_UP for front-end`
- `[BOTTLENECK] Selected front-end for scale-up`
- `[SCALE] front-end → 2 replicas`
- `[EVENT] {...}`
- `SCALE_UP for carts skipped - in cooldown`

## Troubleshooting

### Kafka Connection Errors
```
KafkaError: NoBrokersAvailable
```

**Solution:**
1. Verify Kafka is running: `docker ps | grep kafka`
2. Check bootstrap servers: `echo $KAFKA_BOOTSTRAP_SERVERS`
3. Test connection: `kafka-topics --bootstrap-server localhost:9092 --list`

### Import Errors
```
ModuleNotFoundError: No module named 'kafka'
```

**Solution:**
1. Activate virtual environment
2. Install dependencies: `pip install -r requirements.txt`

### Controller Not Processing
**Symptom:** Tests publish messages but no scaling occurs

**Solution:**
1. Check controller is running: `ps aux | grep controller.py`
2. Verify controller logs show message consumption
3. Check controller is subscribed to correct topics
4. Verify Kubernetes API access (if running in-cluster)

## Next Steps

After all tests pass:
1. ✓ Mark Task 5 as complete
2. Proceed to Phase 5: Kubernetes RBAC and Configuration (Task 6)
3. Continue with experiment tooling (Tasks 8-9)

## Notes

- Quick tests are sufficient for rapid iteration during development
- Full checkpoint tests should be run before marking Task 5 complete
- Tests clear the log file between runs to avoid confusion
- Scale-down test requires patience (~7 minutes) but validates critical functionality
- All tests can be run multiple times without side effects

## Questions or Issues?

If tests fail or behavior is unexpected:
1. Review controller logs for errors
2. Check Kafka topics for messages: `kafka-console-consumer --topic scaling-decisions`
3. Verify controller configuration (environment variables)
4. Ask the user for guidance if issues persist
