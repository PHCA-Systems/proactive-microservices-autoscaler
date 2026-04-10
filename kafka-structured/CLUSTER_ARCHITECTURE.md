# Two-Cluster Architecture for Clean Methodology

## Overview

To ensure methodologically sound experiments, we use **separate clusters** for the application (Sock Shop) and the autoscaling pipeline. This prevents pipeline overhead from affecting Sock Shop metrics and ensures fair comparison between proactive and reactive conditions.

## Cluster Configuration

### Cluster 1: sock-shop-cluster (Application)
- **Purpose:** Runs Sock Shop microservices only
- **Location:** us-central1-a
- **Nodes:** 3× e2-standard-4 (4 vCPU, 16 GB RAM each)
- **Total Resources:** 12 vCPUs, 48 GB RAM
- **Cost:** $0.40/hour
- **Master IP:** 34.66.13.244

**Deployed Services:**
- Sock Shop microservices (7 services: front-end, carts, orders, catalogue, user, payment, shipping)
- Prometheus (for metrics collection)
- HPA (Horizontal Pod Autoscaler) - enabled/disabled per experiment condition

### Cluster 2: pipeline-cluster (Control Plane)
- **Purpose:** Runs autoscaling pipeline infrastructure
- **Location:** us-central1-a
- **Nodes:** 2× e2-standard-2 (2 vCPU, 8 GB RAM each)
- **Total Resources:** 4 vCPUs, 16 GB RAM
- **Cost:** $0.13/hour
- **Master IP:** 136.115.218.105

**Deployed Services:**
- Kafka + Zookeeper (message broker)
- Metrics Aggregator (polls Prometheus)
- ML Inference Services (3 pods: LR, RF, XGB)
- Authoritative Scaler (voting logic)
- Scaling Controller (executes scaling decisions)

## Total Cost

- **Combined:** $0.53/hour
- **8.5-hour experiment:** $4.50
- **Extra cost vs single cluster:** $1.10 (26% increase)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    sock-shop-cluster                        │
│                   (3× e2-standard-4)                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  front-end   │  │    carts     │  │   orders     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  catalogue   │  │     user     │  │   payment    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐                                          │
│  │   shipping   │                                          │
│  └──────────────┘                                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Prometheus (exposed)                     │ │
│  │         http://34.66.13.244:9090                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         HPA (enabled in reactive condition)           │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Prometheus queries
                              │ (HTTP)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   pipeline-cluster                          │
│                   (2× e2-standard-2)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Metrics Aggregator                            │ │
│  │    (polls Prometheus every 30s)                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Kafka + Zookeeper                        │ │
│  │         (topics: metrics, model-votes,                │ │
│  │          scaling-decisions)                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
│                              ▼                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ ML Inf LR  │  │ ML Inf RF  │  │ ML Inf XGB │          │
│  └────────────┘  └────────────┘  └────────────┘          │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Authoritative Scaler                          │ │
│  │         (majority voting)                             │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         Scaling Controller                            │ │
│  │    (makes K8s API calls to sock-shop-cluster)        │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               │ K8s API calls
                               │ (scale deployments)
                               ▼
                    sock-shop-cluster K8s API
```

## Network Configuration

### Prometheus Exposure

Prometheus in sock-shop-cluster needs to be accessible from pipeline-cluster:

**Option 1: LoadBalancer Service (RECOMMENDED)**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: prometheus-server-external
  namespace: sock-shop
spec:
  type: LoadBalancer
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
```

**Option 2: NodePort Service**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: prometheus-server-external
  namespace: sock-shop
spec:
  type: NodePort
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
    nodePort: 30090
```

### Scaling Controller Access

Scaling controller in pipeline-cluster needs to access sock-shop-cluster K8s API:

**Method: Service Account with External Kubeconfig**
1. Create service account in sock-shop-cluster
2. Generate kubeconfig with service account token
3. Mount kubeconfig as secret in scaling-controller pod

## Methodological Benefits

### 1. No Resource Contention
- Sock Shop runs in isolation
- Pipeline overhead doesn't affect Sock Shop metrics
- Both conditions (proactive/reactive) see identical Sock Shop environment

### 2. Preserves Existing Calibration
- SLO threshold (36ms) remains valid
- No need to recalibrate
- Training data remains valid
- ML models don't need retraining

### 3. Fair Comparison
- **Proactive condition:** Pipeline active in pipeline-cluster
- **Reactive condition:** Only HPA active in sock-shop-cluster
- **Both see same Sock Shop baseline performance**

### 4. Publishable Methodology
- Clean separation of concerns
- Easy to defend in paper
- Reviewers can't question validity
- Matches research best practices

## Deployment Order

1. **sock-shop-cluster:**
   - ✅ Cluster created (3 nodes)
   - ✅ Sock Shop deployed
   - ⏳ Expose Prometheus (Task 10.1)

2. **pipeline-cluster:**
   - ✅ Cluster created (2 nodes)
   - ⏳ Deploy Kafka (Task 10.2)
   - ⏳ Deploy pipeline services (Task 10.3)
   - ⏳ Configure cross-cluster access (Task 10.4)

3. **Smoke Tests:** (Task 11)
   - Test proactive condition
   - Test reactive condition
   - Verify no interference

4. **Experiments:** (Task 14)
   - Run 34 experiments
   - Collect results
   - Analyze

## Switching Between Clusters

Use kubectl contexts to switch between clusters:

```bash
# List contexts
kubectl config get-contexts

# Switch to sock-shop cluster
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster

# Switch to pipeline cluster
kubectl config use-context gke_grad-phca_us-central1-a_pipeline-cluster
```

## Cost Optimization

After experiments complete, delete pipeline-cluster to save costs:

```bash
gcloud container clusters delete pipeline-cluster --zone=us-central1-a
```

Sock-shop-cluster can be scaled down to 0 nodes when not in use:

```bash
gcloud container clusters resize sock-shop-cluster --num-nodes=0 --zone=us-central1-a
```

## Notes

- Both clusters in same zone (us-central1-a) for low latency
- Pipeline cluster uses standard disks (not SSD) to avoid quota issues
- Prometheus queries add ~10-50ms latency (negligible)
- K8s API calls from pipeline to sock-shop are authenticated via service account

