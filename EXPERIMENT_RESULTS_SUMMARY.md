# Experiment Results Summary

## Test Configuration

- **Total Runs:** 34
- **Load Patterns:** 4 (constant, step, spike, ramp)
- **Conditions:** 2 (proactive ML-based, reactive HPA baseline)
- **Services Monitored:** 7 (front-end, carts, orders, catalogue, user, payment, shipping)
- **SLO Target:** 35.68ms p95 latency
- **Run Duration:** ~12 minutes per run
- **Metric Collection:** 30-second intervals (20 snapshots per run)
- **Execution Date:** April 13, 2026
- **Total Duration:** 8.2 hours
- **Success Rate:** 100% (34/34 runs completed)

## Global Results

### Key Metrics

| Metric | Proactive | Reactive | Improvement |
|--------|-----------|----------|-------------|
| **SLO Violation Rate** | 19.3% | 26.1% | **6.8 pp reduction** |
| **Mean p95 Latency** | 17.1ms | 82.4ms | **79.3% faster** |
| **Replica-Seconds** | 74,430 | 161,790 | **54.0% savings** |

### Summary

The proactive ML-based autoscaler demonstrates significant advantages over the reactive HPA baseline:

- **Lower SLO Violations:** 19.3% vs 26.1% (6.8 percentage point reduction)
- **Better Latency:** 17.1ms vs 82.4ms average p95 (79.3% improvement)
- **Resource Efficiency:** 54.0% fewer replica-seconds consumed

## Per-Pattern Comparison

### CONSTANT Pattern (2 proactive, 2 reactive runs)

| Service | Pro VR% | Rea VR% | Pro p95 | Rea p95 | Pro RepSec | Rea RepSec | Winner |
|---------|---------|---------|---------|---------|------------|------------|--------|
| front-end | 100.0% | 30.0% | 40.8ms | 334.8ms | 600 | 2,160 | REACTIVE |
| carts | 32.5% | 65.0% | 32.1ms | 94.5ms | 600 | 5,535 | PROACTIVE |
| orders | 10.0% | 75.0% | 27.4ms | 641.9ms | 600 | 600 | PROACTIVE |
| catalogue | 0.0% | 25.0% | 4.8ms | 1108.4ms | 600 | 600 | PROACTIVE |
| user | 0.0% | 20.0% | 5.0ms | 129.3ms | 600 | 600 | PROACTIVE |
| payment | 0.0% | 0.0% | 4.8ms | 4.8ms | 600 | 600 | TIE |
| shipping | 0.0% | 15.0% | 4.8ms | 89.3ms | 600 | 4,635 | PROACTIVE |

**Pattern Winner:** PROACTIVE (5 services) vs REACTIVE (1 service)

### STEP Pattern (5 proactive, 5 reactive runs)

| Service | Pro VR% | Rea VR% | Pro p95 | Rea p95 | Pro RepSec | Rea RepSec | Winner |
|---------|---------|---------|---------|---------|------------|------------|--------|
| front-end | 63.0% | 54.0% | 36.4ms | 86.8ms | 1,158 | 3,612 | REACTIVE |
| carts | 16.0% | 63.0% | 28.9ms | 90.8ms | 600 | 4,602 | PROACTIVE |
| orders | 17.0% | 66.0% | 29.4ms | 139.3ms | 600 | 2,256 | PROACTIVE |
| catalogue | 0.0% | 21.0% | 4.9ms | 288.6ms | 600 | 630 | PROACTIVE |
| user | 0.0% | 22.0% | 5.0ms | 65.8ms | 600 | 600 | PROACTIVE |
| payment | 0.0% | 0.0% | 4.8ms | 4.9ms | 600 | 600 | TIE |
| shipping | 0.0% | 0.0% | 4.8ms | 4.8ms | 600 | 600 | TIE |

**Pattern Winner:** PROACTIVE (4 services) vs REACTIVE (1 service)

### SPIKE Pattern (5 proactive, 5 reactive runs)

| Service | Pro VR% | Rea VR% | Pro p95 | Rea p95 | Pro RepSec | Rea RepSec | Winner |
|---------|---------|---------|---------|---------|------------|------------|--------|
| front-end | 96.0% | 65.0% | 43.8ms | 37.8ms | 600 | 1,122 | REACTIVE |
| carts | 39.0% | 37.0% | 32.0ms | 31.6ms | 600 | 600 | REACTIVE |
| orders | 40.0% | 27.0% | 32.6ms | 40.3ms | 600 | 1,056 | REACTIVE |
| catalogue | 0.0% | 2.0% | 4.8ms | 6.4ms | 600 | 600 | PROACTIVE |
| user | 0.0% | 3.0% | 4.9ms | 7.0ms | 600 | 600 | PROACTIVE |
| payment | 0.0% | 0.0% | 4.8ms | 4.9ms | 600 | 600 | TIE |
| shipping | 0.0% | 0.0% | 4.8ms | 4.8ms | 600 | 600 | TIE |

**Pattern Winner:** REACTIVE (3 services) vs PROACTIVE (2 services)

**Note:** Spike pattern shows reactive HPA performing better, likely due to rapid scaling response to sudden load increases.

### RAMP Pattern (5 proactive, 5 reactive runs)

| Service | Pro VR% | Rea VR% | Pro p95 | Rea p95 | Pro RepSec | Rea RepSec | Winner |
|---------|---------|---------|---------|---------|------------|------------|--------|
| front-end | 94.0% | 66.0% | 39.6ms | 39.4ms | 648 | 1,938 | REACTIVE |
| carts | 34.0% | 56.0% | 33.3ms | 57.6ms | 600 | 3,360 | PROACTIVE |
| orders | 3.0% | 32.0% | 25.0ms | 58.6ms | 600 | 690 | PROACTIVE |
| catalogue | 0.0% | 8.0% | 4.8ms | 11.1ms | 600 | 600 | PROACTIVE |
| user | 0.0% | 8.0% | 4.8ms | 11.0ms | 600 | 600 | PROACTIVE |
| payment | 0.0% | 0.0% | 4.8ms | 4.8ms | 600 | 600 | TIE |
| shipping | 0.0% | 0.0% | 4.8ms | 4.8ms | 600 | 600 | TIE |

**Pattern Winner:** PROACTIVE (4 services) vs REACTIVE (1 service)

## Conclusions

1. **Overall Winner:** Proactive ML-based autoscaler outperforms reactive HPA baseline across most patterns and services
2. **Resource Efficiency:** 54% reduction in replica-seconds demonstrates significant cost savings
3. **Latency Performance:** 79.3% improvement in mean p95 latency
4. **SLO Compliance:** 6.8 percentage point reduction in violation rate
5. **Pattern-Specific Behavior:** Reactive HPA shows competitive performance on spike patterns due to rapid reactive scaling

## Experiment Execution

- **Start Time:** 2026-04-13 06:24:49
- **End Time:** 2026-04-13 14:36:58
- **Duration:** 8.2 hours
- **Runs Completed:** 34/34 (100% success rate)
- **Infrastructure:** GKE clusters, Prometheus monitoring, Locust load generation
- **Results Location:** `kafka-structured/experiments/results/`

---

*Generated: April 13, 2026*
*Analysis: Proactive ML-based Microservices Autoscaler (PHCA) Graduation Project*
