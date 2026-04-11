# Run Load Test for Kubernetes
Write-Host "🚀 Starting Load Test for Kubernetes Sock Shop" -ForegroundColor Green
Write-Host "=" -repeat 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Pattern: Constant Load (50 users)" -ForegroundColor Yellow
Write-Host "Duration: 5 minutes (300 seconds)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop early" -ForegroundColor Red
Write-Host ""

cd load-testing
python -m locust -f src/k8s/locustfile_constant_k8s.py --headless --users 50 --spawn-rate 10 --run-time 300s --html results/k8s_load_test_report.html
