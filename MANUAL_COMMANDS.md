# Manual Commands for Load Testing with Per-Service Metrics

## 🎯 Quick Setup

### For Kubernetes Deployment (Recommended - Auto URL Detection)

#### Terminal 1: Per-Service Metrics Collection
```powershell
cd D:\Projects\Grad\PHCA
phca_venv\Scripts\activate
python collect_per_service_metrics.py --interval 10 --duration 300
```

#### Terminal 2: Load Testing (K8s with Auto-Detection)
```powershell
cd D:\Projects\Grad\PHCA
phca_venv\Scripts\activate
python run_separate_terminals.py --pattern constant --duration 300 --k8s
```

### For Docker Deployment (Original)

#### Terminal 1: Per-Service Metrics Collection
```powershell
cd D:\Projects\Grad\PHCA
phca_venv\Scripts\activate
python collect_per_service_metrics.py --interval 10 --duration 300
```

#### Terminal 2: Load Testing (Docker)
```powershell
cd D:\Projects\Grad\PHCA
phca_venv\Scripts\activate
python run_separate_terminals.py --pattern constant --duration 300 --url http://localhost:80
```

## 📊 Different Load Patterns

### Kubernetes Deployment (Auto URL Detection)
```powershell
# Constant Load (Baseline)
python run_separate_terminals.py --pattern constant --duration 300 --k8s

# Step Load (Burst Testing)
python run_separate_terminals.py --pattern step --duration 600 --k8s

# Spike Load (Flash Crowds)
python run_separate_terminals.py --pattern spike --duration 600 --k8s

# Ramp Load (Organic Growth)
python run_separate_terminals.py --pattern ramp --duration 600 --k8s
```

### Docker Deployment (Manual URL)
```powershell
# Constant Load (Baseline)
python run_separate_terminals.py --pattern constant --duration 300 --url http://localhost:80

# Step Load (Burst Testing)
python run_separate_terminals.py --pattern step --duration 600 --url http://localhost:80

# Spike Load (Flash Crowds)
python run_separate_terminals.py --pattern spike --duration 600 --url http://localhost:80

# Ramp Load (Organic Growth)
python run_separate_terminals.py --pattern ramp --duration 600 --url http://localhost:80
```

## 🔧 URL Detection (K8s Only)

The K8s versions automatically detect the Sock Shop URL:

1. **Check current URL**:
   ```powershell
   kubectl get service front-end -n sock-shop -o jsonpath="{.spec.ports[0].nodePort}"
   minikube ip
   ```

2. **Manual override** (if needed):
   ```powershell
   $env:SOCK_SHOP_URL="http://192.168.49.2:30001"
   python run_separate_terminals.py --pattern constant --duration 300 --k8s
   ```

## 📈 Metrics Collection Options

### Single Collection
```powershell
python collect_per_service_metrics.py --once
```

### Continuous Collection (5-minute intervals)
```powershell
python collect_per_service_metrics.py --interval 15 --duration 300
```

### High-Frequency Collection (every 5 seconds)
```powershell
python collect_per_service_metrics.py --interval 5 --duration 600
```

## 📁 Results Location

- **Per-service metrics**: `results/per_service_metrics_YYYYMMDD_HHMMSS.csv`
- **Load test results**: `load-testing/` directory (CSV files)

## 🎯 Complete Test Workflow

### Kubernetes (Recommended)
1. **Start metrics collection** (Terminal 1)
2. **Wait 10 seconds** for baseline metrics
3. **Start K8s load test** (Terminal 2) - URL auto-detected
4. **Monitor both terminals** during test
5. **Analyze results** after completion

### Docker (Original)
1. **Start metrics collection** (Terminal 1)
2. **Wait 10 seconds** for baseline metrics
3. **Start Docker load test** (Terminal 2) - Manual URL
4. **Monitor both terminals** during test
5. **Analyze results** after completion

## 📊 Expected Per-Service Metrics

You should see output like:
```
rabbitmq        | CPU:  68m | Memory:  123.0MB
front-end       | CPU:  31m | Memory:   73.0MB  (INCREASED UNDER LOAD)
carts           | CPU:   7m | Memory:  117.0MB  
orders          | CPU:   7m | Memory:  114.0MB
... (all 14 services)
TOTAL           | CPU: 176m | Memory: 2041.0MB  (INCREASED UNDER LOAD)
```

## 🚀 Research Data Collection

For comprehensive research data, run all patterns:

### Kubernetes (Auto URL Detection)
```powershell
# Terminal 1: Start long-running metrics collection
python collect_per_service_metrics.py --interval 10 --duration 3000

# Terminal 2: Run all load patterns sequentially
python run_separate_terminals.py --pattern constant --duration 300 --k8s
# Wait 60 seconds between tests
python run_separate_terminals.py --pattern step --duration 600 --k8s
# Wait 60 seconds between tests  
python run_separate_terminals.py --pattern spike --duration 600 --k8s
# Wait 60 seconds between tests
python run_separate_terminals.py --pattern ramp --duration 600 --k8s
```

### Docker (Manual URL)
```powershell
# Terminal 1: Start long-running metrics collection
python collect_per_service_metrics.py --interval 10 --duration 3000

# Terminal 2: Run all load patterns sequentially
python run_separate_terminals.py --pattern constant --duration 300 --url http://localhost:80
# Wait 60 seconds between tests
python run_separate_terminals.py --pattern step --duration 600 --url http://localhost:80
# Wait 60 seconds between tests  
python run_separate_terminals.py --pattern spike --duration 600 --url http://localhost:80
# Wait 60 seconds between tests
python run_separate_terminals.py --pattern ramp --duration 600 --url http://localhost:80
```

## 🎉 Key Improvements

### ✅ What's Fixed
- **Reverted original scripts**: Docker versions use `localhost:80`
- **Separate K8s versions**: Auto-detect URL without hanging processes
- **Dynamic URL detection**: No manual URL commands needed
- **Clean organization**: Clear separation between Docker and K8s versions
- **Robust fallbacks**: Multiple fallback mechanisms for URL detection

### 🎯 Usage Recommendations
- **Use K8s versions** (`--k8s` flag) for current setup
- **Use Docker versions** for original Docker Compose setup
- **Auto URL detection** eliminates manual URL configuration
- **Separate terminals** provide better monitoring and control

This gives you complete per-service resource usage data across all EuroSys'24 load patterns with automatic URL detection! 🎉