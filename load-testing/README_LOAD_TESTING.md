# PHCA Load Testing - EuroSys'24 Compliant

## 📋 Overview

This directory contains EuroSys'24 compliant stochastic load generation scripts for the PHCA microservices autoscaling research project. The load testing implements realistic e-commerce traffic patterns targeting the Sock Shop microservices application.

## 🏗️ Architecture

### Deployment Options

**Docker Deployment (Original)**
- Uses `localhost:80` as target
- Requires manual URL configuration if different
- Files: `locustfile_*.py` (without `_k8s` suffix)

**Kubernetes Deployment (New)**
- Auto-detects Sock Shop URL from minikube service
- Uses kubectl to get NodePort and minikube IP
- Files: `locustfile_*_k8s.py`

## 📁 File Structure

```
load-testing/
├── src/
│   ├── locustfile.py                    # Original comprehensive file
│   ├── locustfile_constant.py           # Docker: Constant load pattern
│   ├── locustfile_constant_k8s.py       # K8s: Constant load pattern
│   ├── locustfile_step.py               # Docker: Step load pattern
│   ├── locustfile_step_k8s.py           # K8s: Step load pattern
│   ├── locustfile_spike.py              # Docker: Spike load pattern
│   ├── locustfile_spike_k8s.py          # K8s: Spike load pattern
│   ├── locustfile_ramp.py               # Docker: Ramp load pattern
│   ├── locustfile_ramp_k8s.py           # K8s: Ramp load pattern
│   └── load_shapes.py                   # Load pattern definitions
├── scripts/
│   └── run_load_test.py                 # Load test runner script
├── config/
│   └── requirements.txt                 # Load testing dependencies
└── docs/
    └── README_LoadTesting.md            # Detailed documentation
```

## 🎯 Load Patterns (EuroSys'24 Compliant)

### 1. Constant Load
- **Purpose**: Baseline steady-state traffic
- **Pattern**: 50 users for 10 minutes
- **Use Case**: Baseline performance measurement

### 2. Step Load
- **Purpose**: Sudden traffic variations
- **Pattern**: Burst increases and decreases
- **Use Case**: Testing autoscaler response to sudden changes

### 3. Spike Load
- **Purpose**: Flash crowd simulation
- **Pattern**: Sharp bursts followed by quiet periods
- **Use Case**: Testing peak load handling

### 4. Ramp Load
- **Purpose**: Organic traffic growth
- **Pattern**: Gradual increase and decrease
- **Use Case**: Testing gradual scaling behavior

## 🚀 Usage

### Docker Deployment
```powershell
# Using run_separate_terminals.py (recommended)
python run_separate_terminals.py --pattern constant --duration 300

# Direct usage
cd load-testing
locust -f src/locustfile_constant.py --headless --users 50 --spawn-rate 5 --run-time 300s --host http://localhost:80
```

### Kubernetes Deployment
```powershell
# Using run_separate_terminals.py with K8s flag (recommended)
python run_separate_terminals.py --pattern constant --duration 300 --k8s

# Direct usage (auto-detects URL)
cd load-testing
locust -f src/locustfile_constant_k8s.py --headless --users 50 --spawn-rate 5 --run-time 300s
```

## 🔧 Dynamic URL Detection (K8s Only)

The K8s versions automatically detect the Sock Shop URL using:

1. **kubectl get service**: Gets the NodePort of front-end service
2. **minikube ip**: Gets the minikube cluster IP
3. **Combines**: Creates `http://{minikube_ip}:{node_port}`
4. **Fallback**: Uses environment variable `SOCK_SHOP_URL` or `http://localhost:80`

**Benefits:**
- No manual URL configuration needed
- Handles dynamic port assignments
- Avoids hanging minikube tunnel processes
- Robust fallback mechanism

## 📊 Stochastic Behavior (EuroSys'24 Compliance)

All load patterns implement:
- **Pure stochastic behavior**: Each user independently selects random actions
- **2-second intervals**: Actions every ~2 seconds per user
- **2-second timeout**: Client-side timeout mimicking user "bouncing"
- **Realistic e-commerce distribution**:
  - ~88% browsing actions
  - ~8.5% add-to-cart actions
  - ~3.4% checkout actions

## 🎯 Integration with Metrics Collection

The load testing integrates seamlessly with the per-service metrics collection:

```powershell
# Simultaneous load testing and metrics collection
python run_separate_terminals.py --pattern constant --duration 300 --k8s --metrics-interval 10
```

This will:
1. Start per-service metrics collection (Terminal 1)
2. Start load testing with auto-detected URL (Terminal 2)
3. Collect performance impact data for ML training

## 📈 Expected Performance Impact

When working correctly, you should see:
- **Front-end service**: Significant CPU increase (300-800%)
- **Other services**: Moderate increases in CPU/memory
- **Overall system**: 30-50% total CPU increase
- **Load test output**: Thousands of successful requests

## 🔍 Troubleshooting

### URL Detection Issues
```powershell
# Test URL detection manually
kubectl get service front-end -n sock-shop -o jsonpath="{.spec.ports[0].nodePort}"
minikube ip
```

### Load Test Not Generating Traffic
- Check if Sock Shop is running: `kubectl get pods -n sock-shop`
- Verify URL is accessible: Open detected URL in browser
- Check load test output for connection errors

### Performance Not Changing
- Ensure using K8s version (`--k8s` flag)
- Verify metrics collection is running
- Check that URL detection is working correctly

## 📚 Research Context

This load testing setup enables:
- **Baseline data collection**: Performance without load
- **Load impact measurement**: Per-service resource usage under load
- **ML training data**: Time-series data for predictive autoscaling
- **Pattern comparison**: Different load patterns for comprehensive analysis

The data collected feeds into the PHCA (Proactive Holistic Context Aware) machine learning models for predictive microservices autoscaling research.