# Task 4.2 Verification: Scale-Down Policy Implementation

## Task Description
Implement scale-down policy that:
- Consumes from `metrics` topic for scale-down evaluation
- Maintains rolling window of last 10 metric snapshots per service
- Checks conditions: CPU < 30%, p95 < 0.7×SLO, replicas > MIN_REPLICAS, not in cooldown
- Decrements replicas by 1 when conditions met for 10 consecutive intervals

## Requirements Coverage

### Requirement 3.1: Scale-Down Evaluation Frequency
✅ **IMPLEMENTED** - Line 249-251 in `controller.py`
```python
# Run scale-down check every 30 seconds
if datetime.now() - last_scaledown_check >= timedelta(seconds=30):
    check_scaledown(apps_v1)
```

### Requirement 3.2: Scale-Down Conditions
✅ **IMPLEMENTED** - Lines 163-199 in `controller.py`

The `check_scaledown()` function evaluates ALL required conditions:

1. **CPU < 30%** (Line 181):
   ```python
   cpu_ok = all(m.get("cpu_usage_pct", 100) < SCALEDOWN_CPU_PCT for m in window)
   ```

2. **p95 < 0.7 × SLO** (Lines 182-185):
   ```python
   lat_ok = all(
       m.get("p95_latency_ms", SLO_THRESHOLD_MS) < SCALEDOWN_LAT_RATIO * SLO_THRESHOLD_MS
       for m in window
   )
   ```

3. **Replicas > MIN_REPLICAS** (Lines 190-191):
   ```python
   if current <= MIN_REPLICAS:
       continue
   ```

4. **Not in cooldown** (Lines 173-174):
   ```python
   if not can_scale(service):
       continue
   ```

5. **10 consecutive intervals** (Lines 177-180):
   ```python
   if len(history) < SCALEDOWN_WINDOW:
       continue
   window = history[-SCALEDOWN_WINDOW:]
   ```

### Requirement 3.3: Scale-Down Action
✅ **IMPLEMENTED** - Lines 193-199 in `controller.py`
```python
target = current - 1
success = set_replicas(apps_v1, service, target)
if success:
    record_scale_event(service)
    log_scale_event(service, "SCALE_DOWN", current, target,
                   reason=f"CPU<{SCALEDOWN_CPU_PCT}% and p95<{SCALEDOWN_LAT_RATIO}×SLO for {SCALEDOWN_WINDOW} intervals")
```

### Requirement 3.4: Rolling Metrics Window
✅ **IMPLEMENTED** - Lines 202-223 in `controller.py`

The `ingest_metric()` function:
1. Consumes metrics from the `metrics` topic (Line 257)
2. Maintains per-service metrics history (Lines 213-219)
3. Limits window size to prevent unbounded growth (Lines 221-222)

```python
def ingest_metric(msg_value: dict):
    """Update rolling metrics window for a service."""
    service = msg_value.get("service")
    if service not in MONITORED_SERVICES:
        return
    
    # Flatten the nested structure if needed
    if "features" in msg_value:
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
```

## Configuration

All scale-down parameters are configurable via environment variables:

- `SCALEDOWN_CPU_PCT`: CPU threshold (default: 30.0%)
- `SCALEDOWN_LAT_RATIO`: Latency ratio threshold (default: 0.7)
- `SCALEDOWN_WINDOW`: Number of consecutive intervals (default: 10)
- `MIN_REPLICAS`: Minimum replica count (default: 1)
- `COOLDOWN_MINUTES`: Cooldown period (default: 5 minutes)

## Test Coverage

All scale-down functionality is verified by `test_scale_down_logic.py`:

1. ✅ **test_scaledown_conditions_met**: Verifies scale-down when all conditions are met
2. ✅ **test_scaledown_insufficient_window**: Verifies no scale-down with < 10 intervals
3. ✅ **test_scaledown_high_cpu**: Verifies no scale-down when CPU exceeds threshold
4. ✅ **test_scaledown_high_latency**: Verifies no scale-down when latency exceeds threshold
5. ✅ **test_scaledown_min_replicas**: Verifies no scale-down at MIN_REPLICAS
6. ✅ **test_scaledown_cooldown**: Verifies cooldown enforcement
7. ✅ **test_scaledown_rolling_window**: Verifies only last 10 intervals are evaluated
8. ✅ **test_scaledown_multiple_services**: Verifies multiple services can scale down
9. ✅ **test_metrics_window_maintenance**: Verifies window size is maintained

## Test Results

```
================================================================================
TASK 4.2 SCALE-DOWN LOGIC TESTS
================================================================================
✓ Scale-down executed when all conditions met for 10 intervals
✓ Scale-down correctly skipped with only 9 intervals (need 10)
✓ Scale-down correctly skipped when CPU exceeded 30% in one interval
✓ Scale-down correctly skipped when p95 latency exceeded threshold in one interval
✓ Scale-down correctly skipped when already at MIN_REPLICAS (1)
✓ Scale-down correctly skipped when service is in cooldown period
✓ Scale-down correctly evaluated only the last 10 intervals
✓ Scale-down correctly executed for multiple services
✓ Metrics window correctly maintained at max size 15

ALL TESTS PASSED ✓
```

## Integration with Existing System

The scale-down policy integrates seamlessly with the existing scaling controller:

1. **Kafka Integration**: Consumes from both `metrics` and `scaling-decisions` topics
2. **Kubernetes Integration**: Uses existing `get_current_replicas()` and `set_replicas()` functions
3. **Cooldown Management**: Uses existing `can_scale()` and `record_scale_event()` functions
4. **Event Logging**: Uses existing `log_scale_event()` function for audit trail

## Conclusion

✅ **Task 4.2 is COMPLETE**

All requirements for the scale-down policy have been implemented and verified:
- Consumes from metrics topic ✓
- Maintains rolling window of 10 snapshots ✓
- Checks all required conditions ✓
- Decrements replicas by 1 ✓
- Enforces cooldown period ✓
- Respects MIN_REPLICAS bound ✓
- Runs every 30 seconds ✓

The implementation is production-ready and fully tested.
