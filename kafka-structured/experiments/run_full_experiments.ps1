# Full Experiment Execution Script (PowerShell)
# This script runs the complete 34-run experiment suite (~8.5 hours)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "PROACTIVE AUTOSCALER EXPERIMENTS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:"
Write-Host "  - Total runs: 34"
Write-Host "  - Duration: ~8.5 hours"
Write-Host "  - Cost: ~`$4.60"
Write-Host ""
Write-Host "Prerequisites:"
Write-Host "  ✓ GKE clusters running" -ForegroundColor Green
Write-Host "  ✓ All services deployed" -ForegroundColor Green
Write-Host "  ✓ Locust VM running" -ForegroundColor Green
Write-Host "  ✓ System validated" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variables
$env:PROMETHEUS_URL = "http://34.170.213.190:9090"
$env:LOCUST_VM_IP = "35.222.116.125"
$env:LOCUST_SSH_USER = "User"
$env:LOCUST_SSH_KEY = "$HOME/.ssh/google_compute_engine"
$env:SOCK_SHOP_EXTERNAL_IP = "104.154.246.88"

# Ensure we're using the correct kubectl context
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster

# Activate virtual environment and run experiments
$venvPath = "..\services\metrics-aggregator\venv\Scripts\Activate.ps1"
& $venvPath

Write-Host "Starting experiment runner..." -ForegroundColor Yellow
Write-Host ""

# Run experiments with pause flag
python run_experiments.py --pause-before-start

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXPERIMENTS COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to: experiments/results/"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run results analyzer: python analyse_results.py"
Write-Host "  2. Review summary.csv and statistics.csv"
Write-Host "  3. Check console output for statistical significance"
Write-Host ""
