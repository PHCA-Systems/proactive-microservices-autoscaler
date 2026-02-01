# Virtual Environment Setup Instructions

## 🐍 Python Virtual Environment Recreation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Step 1: Create Virtual Environment
```powershell
# Windows (PowerShell)
python -m venv phca_venv

# Linux/Mac
python3 -m venv phca_venv
```

### Step 2: Activate Virtual Environment
```powershell
# Windows (PowerShell)
phca_venv\Scripts\activate

# Linux/Mac
source phca_venv/bin/activate
```

### Step 3: Install Dependencies
```powershell
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Verify Setup
```powershell
# Test the setup
python collect_per_service_metrics.py --once
```

## 🔧 Additional Setup (if needed)

### Kubernetes Tools
If you plan to use Kubernetes deployment:
```powershell
# Install kubectl (Windows)
# Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/

# Install minikube (Windows)
# Download from: https://minikube.sigs.k8s.io/docs/start/
```

### Docker Desktop
For Docker deployment:
- Install Docker Desktop from: https://www.docker.com/products/docker-desktop/

## 🎯 Quick Test
After setup, test the system:
```powershell
# Activate environment
phca_venv\Scripts\activate

# Test metrics collection
python collect_per_service_metrics.py --once

# Test load testing (Docker version)
python run_separate_terminals.py --pattern constant --duration 60

# Test load testing (K8s version)
python run_separate_terminals.py --pattern constant --duration 60 --k8s
```

## 📚 Documentation
- Main documentation: `docs/COMPLETE_SETUP_GUIDE.md`
- Load testing guide: `load-testing/README_LOAD_TESTING.md`
- Manual commands: `MANUAL_COMMANDS.md`