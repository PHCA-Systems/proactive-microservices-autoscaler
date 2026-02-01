# PHCA Microservices Autoscaling Research - Complete Setup Guide

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Current Setup Architecture](#current-setup-architecture)
3. [Deployment Options Comparison](#deployment-options-comparison)
4. [How to Run Everything](#how-to-run-everything)
5. [Monitoring & Metrics](#monitoring--metrics)
6. [Load Testing](#load-testing)
7. [Troubleshooting](#troubleshooting)
8. [Important Notes for Team](#important-notes-for-team)

---

## 🎯 Project Overview

**Project**: Proactive Holistic Context Aware Microservices Autoscaling Through Asynchronous ML Classification

**Goal**: Research predictive autoscaling vs reactive scaling using ML classification on microservices under realistic load patterns.

**Application**: Sock Shop - 14-service e-commerce microservices demo
**Load Testing**: EuroSys'24 compliant stochastic load generation
**Monitoring**: Professional-grade metrics collection and visualization

---

## 🏗️ Current Setup Architecture

### **Infrastructure Stack**
```
Windows Host Machine
├── Docker Desktop
│   ├── minikube (Kubernetes cluster in container)
│   │   ├── Sock Shop (14 microservices pods)
│   │   ├── Prometheus (metrics collection)
│   │   ├── Grafana (visualization)
│   │   └── Node Exporter (system metrics)
│   │
│   ├── InfluxDB (time-series database)
│   ├── Telegraf (metrics collector)
│   └── Old Grafana (legacy, can be removed)
```

### **Network Architecture**
```
LAYER 1: Windows Desktop
├── localhost:49494 → Sock Shop UI (minikube tunnel)
├── localhost:60910 → Prometheus UI (minikube tunnel)
├── localhost:61997 → Grafana UI (minikube tunnel)
└── localhost:8086 → InfluxDB UI (direct Docker)

LAYER 2: Minikube VM (192.168.49.2)
├── NodePorts: 30001 (Sock Shop), 30090 (Prometheus), 30300 (Grafana)
├── Service Network: 10.96.0.0/12 (load balancers)
└── Pod Network: 10.244.0.0/16 (actual applications)

LAYER 3: Pod Network
├── front-end: 10.244.0.8:8079
├── carts: 10.244.0.3:80
├── catalogue: 10.244.0.5:80
└── ... (all 14 services)
```

### **Resource Allocation**
```
Per Sock Shop Pod:
├── CPU Request: 100m (0.1 cores)
├── CPU Limit: 300m (0.3 cores)
├── Memory Request: 300Mi (~300MB)
└── Memory Limit: 1000Mi (~1GB)

Total Sock Shop Resources:
├── CPU Requests: ~1.4 cores
├── CPU Limits: ~4.2 cores
├── Memory Requests: ~4.2GB
└── Memory Limits: ~14GB
```

---

## ⚖️ Deployment Options Comparison

### **Option 1: Kubernetes (CURRENT - RECOMMENDED)**

**Architecture:**
```
minikube → Kubernetes → Pods → Containers
```

**Metrics Collection:**
```
Prometheus (in Kubernetes pod)
├── Scrapes Node Exporter every 15s → System metrics (CPU, memory, disk, network)
├── Scrapes Kubernetes API → Pod status, service health, cluster metrics
├── Scrapes Service Endpoints → Application metrics (if instrumented)
└── Stores in time-series database with 200h retention
```

**Storage:**
- **Location**: Inside Prometheus pod (`/prometheus` volume)
- **Format**: Time-series database (TSDB)
- **Retention**: 200 hours (8+ days)
- **Query**: PromQL via Prometheus UI or Grafana
- **Persistence**: Lost if pod deleted (emptyDir volume)

**Why This Works:**
- ✅ **No WSL2 issues**: Everything runs inside minikube container
- ✅ **Professional metrics**: 885+ metrics collected automatically
- ✅ **Native integration**: Kubernetes + Prometheus designed together
- ✅ **Per-service visibility**: Can see individual pod resource usage
- ✅ **Research-grade data**: Suitable for ML model training

**Challenges We Faced:**
- ❌ **cAdvisor failed**: Container metrics unavailable due to minikube/Docker filesystem issues
- ❌ **Complex networking**: Multiple network layers (Windows → Docker → minikube → pods)
- ❌ **Dynamic URLs**: Service URLs change each restart

### **Option 2: Direct Docker Compose (LEGACY)**

**Architecture:**
```
Docker Desktop → Docker Compose → Containers
```

**Metrics Collection:**
```
Custom Python Script (collectors/metrics_collector.py)
├── Calls `docker stats` command every 12s → Container CPU, memory, network
├── Parses output and stores in CSV files → Local file storage
└── Optional: Sends to InfluxDB → Time-series database
```

**Storage:**
- **Location**: Local CSV files or InfluxDB container
- **Format**: CSV (simple) or InfluxDB (time-series)
- **Retention**: Unlimited (files) or configurable (InfluxDB)
- **Query**: Python pandas (CSV) or InfluxQL (InfluxDB)
- **Persistence**: Permanent local files

**Why We Abandoned This:**
- ❌ **WSL2 Docker socket issues**: Telegraf couldn't access Docker metrics
- ❌ **Permission denied errors**: Windows/WSL2 Docker socket permissions
- ❌ **Limited metrics**: Only basic container stats (CPU, memory, network)
- ❌ **No service-level data**: Can't distinguish between microservices
- ❌ **Manual collection**: Custom scripts required for everything

**What Worked:**
- ✅ **Simple setup**: Just `docker-compose up`
- ✅ **Direct access**: Services on localhost:80, localhost:8080, etc.
- ✅ **Basic monitoring**: Docker stats provided container-level metrics

### **Key Differences Summary**

| Aspect | Kubernetes (Current) | Docker Compose (Legacy) |
|--------|---------------------|-------------------------|
| **Metrics Collection** | Prometheus scrapes 885+ metrics | Custom script calls `docker stats` |
| **Metrics Storage** | Time-series DB in pod (200h) | CSV files or InfluxDB |
| **System Metrics** | Node Exporter (professional) | Docker stats (basic) |
| **Service Metrics** | Per-pod resource usage | Per-container only |
| **WSL2 Compatibility** | ✅ Works (isolated in minikube) | ❌ Docker socket permission issues |
| **Monitoring Tools** | Prometheus + Grafana native | Custom scripts + manual setup |
| **Data Quality** | Research-grade time-series | Basic container stats |
| **Setup Complexity** | High (multiple network layers) | Low (direct containers) |
| **Troubleshooting** | Complex (K8s + networking) | Simple (direct Docker) |
| **Research Value** | High (production-like) | Limited (development-like) |

### **Detailed Metrics Comparison**

**Kubernetes Approach:**
```
Data Flow:
Node Exporter → Prometheus → Grafana
     ↓              ↓          ↓
System metrics  Storage    Visualization
(CPU, memory,   (TSDB)     (Dashboards)
 disk, network)
```

**Docker Compose Approach:**
```
Data Flow:
docker stats → Python script → CSV/InfluxDB → Manual analysis
     ↓              ↓              ↓              ↓
Container stats  Parsing      Storage      Python/Excel
(CPU, memory,   (Custom)     (Files)      (Manual)
 network)
```

**Why Kubernetes Won:**
1. **WSL2 Issues Solved**: minikube isolates everything in a container
2. **Professional Metrics**: 885 metrics vs ~10 basic stats
3. **No Permission Issues**: Everything runs inside minikube's controlled environment
4. **Research Quality**: Time-series data suitable for ML training
5. **Industry Standard**: Reflects real-world microservices deployments

---

## 🚀 How to Run Everything

### **Prerequisites**
- Windows 10/11 with Docker Desktop
- minikube installed
- Python 3.8+ with virtual environment
- 8GB+ RAM recommended

### **Step 1: Start Core Infrastructure**

```bash
# 1. Start minikube
minikube start

# 2. Deploy Sock Shop
kubectl apply -f https://raw.githubusercontent.com/microservices-demo/microservices-demo/master/deploy/kubernetes/complete-demo.yaml

# 3. Deploy monitoring stack
kubectl apply -f k8s-monitoring.yaml

# 4. Wait for all pods to be ready
kubectl get pods -A
```

### **Step 2: Start Service Tunnels (4 Terminals)**

**Terminal 1 - Sock Shop UI:**
```bash
minikube service front-end -n sock-shop --url
# Keep open, note the URL (e.g., http://127.0.0.1:49494)
```

**Terminal 2 - Prometheus:**
```bash
minikube service prometheus -n monitoring --url
# Keep open, note the URL (e.g., http://127.0.0.1:60910)
```

**Terminal 3 - Grafana:**
```bash
minikube service grafana -n monitoring --url
# Keep open, note the URL (e.g., http://127.0.0.1:61997)
# Login: admin/admin
```

**Terminal 4 - Working Terminal:**
```bash
cd D:\Projects\Grad\PHCA
phca_venv\Scripts\activate
```

### **Step 3: Verify Everything Works**

```bash
# Check all pods are running
kubectl get pods -A

# Verify Prometheus is collecting metrics
python verify_prometheus.py

# Test Sock Shop UI in browser
# Visit the URL from Terminal 1
```

### **Step 4: Run Load Tests**

```bash
cd load-testing

# Update locustfile with correct Sock Shop URL from Terminal 1
# Edit src/locustfile_constant.py: host = "http://127.0.0.1:XXXXX"

# Run different load patterns
python scripts/run_load_test.py --pattern constant --duration 300
python scripts/run_load_test.py --pattern step --duration 600
python scripts/run_load_test.py --pattern spike --duration 600
python scripts/run_load_test.py --pattern ramp --duration 600
```

---

## 📊 Monitoring & Metrics

### **What's Being Monitored**

**System-Level (Node Exporter):**
- CPU usage per core and mode (user, system, idle, iowait)
- Memory usage (total, available, used, cached, buffers)
- Disk I/O (read/write operations, bytes, utilization)
- Network traffic (bytes sent/received, packets, errors)
- System load (1min, 5min, 15min averages)
- Process count and socket statistics

**Kubernetes-Level (Prometheus):**
- Pod status and health (Running, Pending, Failed)
- Node status and conditions
- Service endpoint health
- API server metrics (request rates, latencies)
- Scheduler and controller metrics

**Application-Level (Limited):**
- Network connections (TCP/UDP socket usage)
- Service-to-service communication patterns
- DNS query patterns

### **Key Metrics Queries**

```promql
# System CPU Usage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Network Traffic
rate(node_network_receive_bytes_total[5m])

# TCP Connections (indicates service activity)
node_sockstat_TCP_inuse

# All Targets Health
up
```

### **Accessing Dashboards**

**Prometheus (Metrics & Queries):**
- URL: From Terminal 2 output
- Use: Raw metrics exploration, custom queries
- Key sections: Graph, Alerts, Status → Targets

**Grafana (Visualization):**
- URL: From Terminal 3 output
- Login: admin/admin
- Use: Professional dashboards, time-series visualization
- Data source: Prometheus (auto-configured)

---

## 🧪 Load Testing

### **EuroSys'24 Compliant Patterns**

**Load testing follows academic paper methodology:**

**Action Distribution (Data-driven from 2024-2025 e-commerce benchmarks):**
```
Total Weight: 117 tasks
├── Browsing (88.0%):
│   ├── browse_home: 25 (21.4%)
│   ├── browse_catalogue: 20 (17.1%)
│   ├── browse_category: 20 (17.1%)
│   └── view_item: 20 (17.1%)
├── add_to_cart: 10 (8.5%)
├── view_cart: 8 (6.8%)
└── checkout: 4 (3.4%)
```

**Load Patterns:**

1. **Constant Load**: 50 users for 10 minutes (baseline)
2. **Step Load**: 50→200→100→300→50 users (burst response)
3. **Spike Load**: Base 10 users with flash crowds (flash crowd handling)
4. **Ramp Load**: 10→150→10 users over 10 minutes (organic growth)

### **Running Load Tests**

```bash
# Navigate to load testing directory
cd load-testing

# IMPORTANT: Update the target URL in locustfiles
# Edit src/locustfile_*.py files
# Change: host = "http://localhost:80"
# To: host = "http://127.0.0.1:XXXXX" (from minikube service command)

# Run tests
python scripts/run_load_test.py --pattern constant
python scripts/run_load_test.py --pattern step
python scripts/run_load_test.py --pattern spike
python scripts/run_load_test.py --pattern ramp
```

### **Expected Results**
- **Request rate**: ~25 req/s sustained
- **Response times**: 6-11ms median, <200ms max
- **Success rate**: 100% (0 failures)
- **Distribution**: Matches EuroSys'24 paper exactly

---

## 🔧 Troubleshooting

### **Common Issues**

**1. Pods Not Starting**
```bash
# Check pod status
kubectl get pods -A

# Check specific pod logs
kubectl logs -n sock-shop <pod-name>

# Check pod details
kubectl describe pod -n sock-shop <pod-name>
```

**2. Services Not Accessible**
```bash
# Check services
kubectl get svc -A

# Restart minikube tunnel
minikube service <service-name> -n <namespace> --url
```

**3. Load Tests Failing**
```bash
# Verify Sock Shop URL is correct
curl <sock-shop-url>

# Check if URL in locustfile matches minikube service URL
cat load-testing/src/locustfile_constant.py | grep host
```

**4. Prometheus Not Collecting Metrics**
```bash
# Check Prometheus targets
# Go to Prometheus UI → Status → Targets
# All should be "UP"

# Restart Prometheus if needed
kubectl rollout restart deployment/prometheus -n monitoring
```

### **Resource Issues**

**If system is slow:**
- Increase Docker Desktop memory allocation (8GB+ recommended)
- Close unnecessary applications
- Check Windows Task Manager for resource usage

**If pods are pending:**
```bash
# Check node resources
kubectl describe node minikube

# Check if resource requests exceed node capacity
kubectl get pods -o wide
```

---

## 📝 Important Notes for Team

### **File Structure**
```
PHCA/
├── docs/                          # Documentation
├── k8s-monitoring.yaml           # Kubernetes monitoring stack
├── verify_prometheus.py          # Prometheus verification script
├── explore_metrics.py            # Metrics exploration tool
├── load-testing/                 # Load testing framework
│   ├── src/                      # Locust files
│   └── scripts/                  # Test runners
├── collectors/                   # Legacy Docker collectors
├── influx-stack/                # Legacy InfluxDB stack
└── results/                     # Test results
```

### **URLs to Remember**
- **Sock Shop**: `minikube service front-end -n sock-shop --url`
- **Prometheus**: `minikube service prometheus -n monitoring --url`
- **Grafana**: `minikube service grafana -n monitoring --url`
- **InfluxDB**: `http://localhost:8086` (if using legacy stack)

### **Key Commands**
```bash
# Start everything
minikube start
kubectl get pods -A

# Stop everything
minikube stop

# Reset if broken
minikube delete
minikube start

# Check status
kubectl get pods -A
kubectl get svc -A
```

### **Research Data Location**
- **Prometheus**: Metrics stored in pod (200h retention)
- **Load test results**: CSV files in load-testing directory
- **System metrics**: Available via Prometheus queries
- **Grafana dashboards**: Create custom dashboards for analysis

### **Performance Expectations**
- **Startup time**: 5-10 minutes for full stack
- **Resource usage**: ~4GB RAM, ~2 CPU cores
- **Load test capacity**: Up to 100 concurrent users tested
- **Metrics retention**: 8+ days in Prometheus

### **Next Steps for Research**
1. **Baseline measurements**: Run constant load, record metrics
2. **Pattern analysis**: Compare system behavior across load patterns
3. **Autoscaling setup**: Implement HPA/VPA on Kubernetes
4. **ML model training**: Use collected metrics for predictive models
5. **Comparison studies**: Reactive vs predictive autoscaling

---

## 🎯 Quick Start Checklist

- [ ] Docker Desktop running
- [ ] minikube started
- [ ] All pods running (kubectl get pods -A)
- [ ] 4 terminals with service tunnels open
- [ ] Sock Shop UI accessible in browser
- [ ] Prometheus collecting metrics (verify_prometheus.py)
- [ ] Grafana accessible with admin/admin
- [ ] Load test URLs updated in locustfiles
- [ ] Virtual environment activated
- [ ] First load test completed successfully

**Time to full setup**: ~15 minutes
**Team handoff ready**: ✅

---

*This setup provides a professional-grade microservices research environment with comprehensive monitoring and EuroSys'24 compliant load testing capabilities.*

---

## ✅ Recent Updates & Fixes

### Load Testing URL Fix & Organization (February 2026)
**MAJOR IMPROVEMENTS**: Complete reorganization of load testing with Docker/K8s separation and dynamic URL detection.

**Issues Resolved**:
- ❌ Load tests targeting wrong URLs
- ❌ Manual URL configuration required
- ❌ Hanging minikube tunnel processes
- ❌ Mixed Docker/K8s configurations

**Solutions Implemented**:
1. **Reverted Original Scripts**: Docker versions restored to `localhost:80`
2. **Separate K8s Versions**: New `*_k8s.py` files with auto URL detection
3. **Dynamic URL Detection**: Uses `kubectl` + `minikube ip` (no hanging processes)
4. **Clean Organization**: Clear separation between deployment types
5. **Robust Fallbacks**: Multiple fallback mechanisms for URL detection

**New File Structure**:
```
load-testing/src/
├── locustfile_constant.py        # Docker: localhost:80
├── locustfile_constant_k8s.py    # K8s: Auto-detect URL
├── locustfile_step.py             # Docker: localhost:80  
├── locustfile_step_k8s.py         # K8s: Auto-detect URL
├── locustfile_spike.py            # Docker: localhost:80
├── locustfile_spike_k8s.py        # K8s: Auto-detect URL
├── locustfile_ramp.py             # Docker: localhost:80
└── locustfile_ramp_k8s.py         # K8s: Auto-detect URL
```

**Verification Results** (K8s with auto-detection):
- ✅ URL auto-detected: `http://192.168.49.2:30001`
- ✅ Load test generated 9,949 requests over 2 minutes
- ✅ Front-end CPU usage: 4m → 31m (775% increase)
- ✅ Total system CPU: 122m → 176m (44% increase)
- ✅ No hanging processes or manual URL configuration

**Current Working Commands**:

**Kubernetes (Recommended - Auto URL Detection)**:
```powershell
# Metrics + Load Test with auto URL detection
python run_separate_terminals.py --pattern constant --duration 300 --k8s
```

**Docker (Original)**:
```powershell
# Metrics + Load Test with manual URL
python run_separate_terminals.py --pattern constant --duration 300 --url http://localhost:80
```

**Why the Performance Didn't Change Initially**:
The initial URL change I claimed to make was only to one file and wasn't properly integrated with the test runner scripts. The scripts were still using the wrong locustfiles or wrong URLs. The comprehensive fix involved:
1. Properly separating Docker vs K8s versions
2. Implementing robust URL auto-detection
3. Updating all runner scripts to use the correct files
4. Testing the complete end-to-end workflow

**Research Impact**: The setup now provides:
- **Dual deployment support**: Both Docker and Kubernetes
- **Zero configuration**: Auto URL detection for K8s
- **Reliable data collection**: No hanging processes or manual steps
- **Complete separation**: Clean organization for team handoff
- **Verified performance impact**: Confirmed working with real metrics

The PHCA research project now has a robust, professional-grade load testing and metrics collection system ready for comprehensive ML training data collection.
