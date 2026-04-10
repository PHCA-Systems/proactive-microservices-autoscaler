# Task 8.2: Condition Switching - COMPLETE

## Summary

Task 8.2 has been completed. The three condition switching functions are implemented in `run_experiments.py`:

1. **`enable_proactive()`** - Enables proactive autoscaling
2. **`enable_reactive()`** - Enables reactive HPA baseline
3. **`reset_cluster()`** - Resets all services to 1 replica

## Implementation Details

### 1. `enable_proactive()`

**Purpose:** Enable the proactive ML-based autoscaling system

**Actions:**
- Deletes HPA resources for all 7 monitored services
- Scales `scaling-controller` deployment to 1 replica
- Waits 15 seconds for controller to start

**Requirements Met:**
- Requirement 6.3: Enable proactive condition
- Requirement 10.5: Delete HPA resources

**Code Location:** `kafka-structured/experiments/run_experiments.py:50-80`

### 2. `enable_reactive()`

**Purpose:** Enable the reactive CPU-based HPA baseline

**Actions:**
- Scales `scaling-controller` deployment to 0 replicas
- Applies HPA manifests from `k8s/hpa-baseline.yaml` using kubectl
- Waits 15 seconds for HPA to initialize

**Requirements Met:**
- Requirement 6.4: Enable reactive condition
- Requirement 10.4: Apply HPA resources

**Code Location:** `kafka-structured/experiments/run_experiments.py:83-115`

### 3. `reset_cluster()`

**Purpose:** Reset all monitored services to a consistent starting state

**Actions:**
- Sets all 7 monitored services to 1 replica
- Waits 2 minutes for pods to stabilize
- Reports success/failure for each service

**Requirements Met:**
- Requirement 6.2: Reset cluster before each run
- Requirement 10.4: Set all services to 1 replica

**Code Location:** `kafka-structured/experiments/run_experiments.py:24-47`

## Monitored Services

All three functions operate on the 7 monitored services defined in `run_config.py`:

1. front-end
2. carts
3. orders
4. catalogue
5. user
6. payment
7. shipping

## HPA Configuration

The HPA baseline (`k8s/hpa-baseline.yaml`) configures:
- Target: 70% CPU utilization
- Min replicas: 1
- Max replicas: 10
- Scale-down stabilization: 300 seconds (5 minutes)

## Error Handling

All three functions include error handling:
- **404 errors** (resource not found) are logged as warnings
- **Other API errors** are logged but don't stop execution
- **Missing HPA file** is logged as an error in `enable_reactive()`
- **kubectl failures** are logged with stderr output

## Testing

A comprehensive test script has been created: `test_condition_switching.py`

**Test Coverage:**
1. Test `reset_cluster()` - Verifies all services set to 1 replica
2. Test `enable_proactive()` - Verifies controller=1, HPAs=0
3. Test `enable_reactive()` - Verifies controller=0, HPAs=7
4. Test condition switching - Verifies proactive→reactive→proactive transitions

**To Run Tests:**
```bash
cd kafka-structured/experiments
python test_condition_switching.py
```

**Prerequisites:**
- Connected to GKE cluster (kubeconfig configured)
- `sock-shop` namespace exists
- All 7 monitored services deployed
- `scaling-controller` deployment exists

## Integration with Experiment Runner

These functions are called by `execute_run()` in the experiment runner:

```python
def execute_run(run: ExperimentRun) -> Path:
    # Switch condition
    if run.condition == "proactive":
        enable_proactive()
    else:
        enable_reactive()
    
    reset_cluster()
    
    # ... collect metrics for 12 minutes ...
```

**Execution Order:**
1. Enable condition (proactive or reactive)
2. Reset cluster to 1 replica
3. Start load generator
4. Collect metrics for 12 minutes
5. Stop load generator and settle for 3 minutes

## Verification Checklist

- [x] `reset_cluster()` implemented
- [x] `enable_proactive()` implemented
- [x] `enable_reactive()` implemented
- [x] Error handling for API failures
- [x] Error handling for missing resources
- [x] Proper wait times for stabilization
- [x] Logging for all operations
- [x] Test script created
- [x] Documentation complete

## Requirements Traceability

| Requirement | Function | Status |
|-------------|----------|--------|
| 6.2 | `reset_cluster()` | ✓ Complete |
| 6.3 | `enable_proactive()` | ✓ Complete |
| 6.4 | `enable_reactive()` | ✓ Complete |
| 10.4 | `enable_reactive()` | ✓ Complete |
| 10.5 | `enable_proactive()` | ✓ Complete |

## Next Steps

Task 8.2 is complete. The next task is:

**Task 8.3:** Implement metrics collection
- Query replica counts from Kubernetes API
- Query p95 latency and CPU from Prometheus
- Construct snapshot with all required fields
- Calculate SLO violation flag

## Notes

- The implementation uses the Kubernetes Python client for API calls
- HPA application uses `kubectl apply` via subprocess (simpler than constructing HPA objects)
- All functions include appropriate wait times for Kubernetes to process changes
- The test script provides comprehensive verification of all three functions
