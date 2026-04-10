# Dataset Comparison: Local vs GKE Mixed

## Quick Facts

| Characteristic | Local | GKE Mixed | Difference |
|----------------|-------|-----------|------------|
| **File** | `mixed_4hour_metrics.csv` | `gke_mixed_dataset.csv` | - |
| **Total Rows** | 3,500 | 3,570 | +70 (+2%) |
| **Violations** | 592 (16.9%) | 475 (13.3%) | -117 (-3.6%) |
| **Services** | 7 | 7 | Same |
| **Duration** | ~4 hours | ~4 hours | Same |
| **Workload Type** | Mixed patterns | Mixed patterns | Same |
| **Environment** | Docker (single host) | GKE (distributed cloud) | **KEY DIFFERENCE** |
| **Infrastructure** | Consistent | Variable | **KEY DIFFERENCE** |
| **Test Set Size** | 700 (20%) | 714 (20%) | +14 (+2%) |

## Critical Observations

### 1. Nearly Identical Dataset Characteristics
- Both are 4-hour continuous runs with mixed load patterns
- Similar sizes: 3,500 vs 3,570 samples (only 2% difference)
- Same 7 microservices
- Both use same features and preprocessing

### 2. Key Differences Are Environmental
- **Local**: Docker containers on single machine
  - Consistent resource allocation
  - Predictable network latency
  - Stable infrastructure
  - Lower environmental noise

- **GKE**: Distributed Kubernetes cluster
  - Variable resource allocation across nodes
  - Dynamic network latency
  - Pod scheduling variability
  - Complex infrastructure patterns

### 3. Violation Rate Difference
- Local: 16.9% (more imbalanced)
- GKE: 13.3% (more balanced)
- This 3.6% difference affects model optimization

## Why This Matters for Model Performance

### Models Specialize on Local (Consistent Environment)
- XGBoost: Optimizes for accuracy/F1 through precise gradients
- Random Forest: Optimizes for ROC-AUC through probability calibration
- Logistic Regression: Optimizes for recall through threshold tuning
- Each model finds its niche in the consistent environment

### Random Forest Dominates on GKE (Complex Environment)
- 200 trees handle infrastructure variability
- Each tree specializes in different node/network scenarios
- Bagging averages out environment-specific noise
- Ensemble robustness wins in complex cloud infrastructure

## Conclusion

The datasets are nearly identical in size and workload type. The performance difference is NOT due to:
- ❌ Dataset size (3,500 vs 3,570 is negligible)
- ❌ Pattern complexity (both are mixed workloads)
- ❌ Number of patterns (both have mixed patterns)

The performance difference IS due to:
- ✅ Environment complexity (Docker vs Cloud)
- ✅ Infrastructure variability (single host vs distributed)
- ✅ Resource allocation patterns (consistent vs variable)
- ✅ Network characteristics (predictable vs dynamic)

**Bottom Line**: Random Forest dominates on GKE because cloud infrastructure is complex and variable, not because the dataset is larger or has more patterns. The environment matters more than the data.
