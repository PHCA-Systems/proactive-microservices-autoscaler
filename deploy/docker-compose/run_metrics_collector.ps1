# Autoscaling Metrics Collector - PowerShell Script
# This script runs the metrics collector

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting metrics collector..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python collect_autoscaling_metrics.py

