#!/bin/bash
# Full Experiment Execution Script
# This script runs the complete 34-run experiment suite (~8.5 hours)

set -e

echo "=========================================="
echo "PROACTIVE AUTOSCALER EXPERIMENTS"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Total runs: 34"
echo "  - Duration: ~8.5 hours"
echo "  - Cost: ~$4.60"
echo ""
echo "Prerequisites:"
echo "  ✓ GKE clusters running"
echo "  ✓ All services deployed"
echo "  ✓ Locust VM running"
echo "  ✓ System validated"
echo ""
echo "=========================================="
echo ""

# Activate virtual environment
source ../services/metrics-aggregator/venv/bin/activate

# Set environment variables
export PROMETHEUS_URL="http://34.170.213.190:9090"
export LOCUST_VM_IP="35.222.116.125"
export LOCUST_SSH_USER="User"
export LOCUST_SSH_KEY="$HOME/.ssh/google_compute_engine"
export SOCK_SHOP_EXTERNAL_IP="104.154.246.88"

# Ensure we're using the correct kubectl context
kubectl config use-context gke_grad-phca_us-central1-a_sock-shop-cluster

# Run experiments with pause flag
echo "Starting experiment runner..."
echo ""
python run_experiments.py --pause-before-start

echo ""
echo "=========================================="
echo "EXPERIMENTS COMPLETE"
echo "=========================================="
echo ""
echo "Results saved to: experiments/results/"
echo ""
echo "Next steps:"
echo "  1. Run results analyzer: python analyse_results.py"
echo "  2. Review summary.csv and statistics.csv"
echo "  3. Check console output for statistical significance"
echo ""
