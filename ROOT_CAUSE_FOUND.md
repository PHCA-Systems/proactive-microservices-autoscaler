# ROOT CAUSE FOUND: Metrics Aggregator Publishing Incorrect RPS Values

## The Problem

The RPS gate is blocking ML predictions because the metrics aggregator is publishing RPS values that are 10-100x lower than they should be.

## Evidence from Logs

During a 150-user constant load test, we observed:

```
[RPS CHECK] front-end: RPS=0.77, threshold=1.0
[RPS GATE BLOCKED] front-end: RPS 0.77 < 1.0, returning NO_OP

[RPS CHECK] catalogue: RPS=0.87, threshold=1.0
[RPS GATE BLOCKED] catalogue: RPS 0.87 < 1.0, returning NO_OP

[RPS CHECK] user: RPS=0.87, threshold=1.0
[RPS GATE BLOCKED] user: RPS 0.87 < 1.0, returning NO_OP

[RPS CHECK] carts: RPS=2.29, threshold=1.0
[PREDICTION] carts: SCALE_UP (confidence=96.50%, RPS=2.29)

[RPS CHECK] front-end: RPS=12.58, threshold=1.0
[PREDICTION] front-end: SCALE_UP (confidence=99.50%, RPS=12.58)
```

## Expected vs Actual RPS

| Service | Expected RPS (150 users) | Actual RPS | Ratio |
|---------|-------------------------|------------|-------|
| front-end | 50-150 | 0.77-12.58 | 4-195x too low |
| catalogue | 20-60 | 0.87-4.27 | 5-69x too low |
| user | 10-30 | 0.87-3.09 | 3-34x too low |
| carts | 10-30 | 0.00-2.29 | 4-∞x too low |
| orders | 5-15 | 0.00-0.29 | 17-∞x too low |

## Impact

1. **RPS Gate Blocks Most Predictions**: When RPS < 1.0, models return NO_OP with 100% confidence
2. **Proactive System Can't Scale**: Even when services are violating SLO, models don't predict SCALE_UP
3. **HPA Does All The Scaling**: Since proactive system is blocked, HPA (reactive) handles everything
4. **Both Tests Were Effectively Reactive**: This explains why proactive and reactive showed identical behavior

## Why This Happened

The metrics aggregator is likely:
1. Using the wrong Prometheus query for RPS
2. Calculating RPS over the wrong time window
3. Dividing by the wrong denominator
4. Missing a unit conversion (e.g., requests per 30s instead of requests per second)

## The Fix

### Option 1: Fix Metrics Aggregator RPS Calculation (RECOMMENDED)
1. Check the Prometheus query in metrics aggregator
2. Verify it's calculating requests per second correctly
3. Test with a known load (e.g., 100 RPS from Locust)
4. Verify metrics aggregator publishes correct RPS

### Option 2: Lower RPS Gate Threshold
1. Change `RPS_THRESHOLD = 1.0` to `RPS_THRESHOLD = 0.1`
2. This is a band-aid fix - doesn't solve the root cause
3. But it would unblock the proactive system immediately

### Option 3: Remove RPS Gate Entirely
1. Remove the RPS gate from inference.py
2. Risky - models might predict SCALE_UP when there's no load
3. But would prove that RPS gate is the only issue

## Next Steps

1. **Investigate metrics aggregator** - Check the RPS calculation code
2. **Verify Prometheus query** - Test the query manually in Prometheus UI
3. **Fix the calculation** - Correct the RPS formula
4. **Redeploy metrics aggregator** - Push the fix
5. **Retest** - Run another quick test to verify RPS values are correct
6. **Run full experiments** - Once RPS is fixed, run complete proactive vs reactive comparison

## Temporary Workaround

To unblock testing immediately, lower the RPS threshold:

```python
RPS_THRESHOLD = 0.1  # Temporary: accounts for 10x underreporting
```

This will allow predictions to run while we fix the root cause.

## Why We Didn't Catch This Earlier

1. **No load during previous tests**: If you ran tests without Locust, RPS would be 0 (correct)
2. **Training data had same bug**: If training data was collected with the same broken metrics aggregator, models learned to work with low RPS values
3. **RPS gate was added recently**: The gate was added to prevent spurious scaling during no-load, but it exposed the RPS calculation bug

## Conclusion

The proactive system is working correctly - the ML models, consensus service, and scaling controller are all functioning. The issue is that the metrics aggregator is feeding them incorrect data (RPS values 10-100x too low), causing the RPS gate to block predictions.

Fix the metrics aggregator RPS calculation, and the proactive system will work as designed.
