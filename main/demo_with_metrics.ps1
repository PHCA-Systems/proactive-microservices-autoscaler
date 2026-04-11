# Complete Demo: Watch Metrics + Run Load Test
Write-Host "🎯 Starting Sock Shop Load Test Demo" -ForegroundColor Cyan
Write-Host "=" -repeat 60 -ForegroundColor Cyan
Write-Host ""

# Check status
Write-Host "📋 Checking pods..." -ForegroundColor Yellow
$running = kubectl get pods -n sock-shop --no-headers | Where-Object { $_ -match "Running" } | Measure-Object -Line
Write-Host "   Running pods: $($running.Lines)/14" -ForegroundColor Green
Write-Host ""

if ($running.Lines -lt 14) {
    Write-Host "⚠️  Not all pods are running! Wait for them to start." -ForegroundColor Red
    exit
}

# Show baseline
Write-Host "📊 Current Baseline Metrics:" -ForegroundColor Yellow
kubectl top pods -n sock-shop
Write-Host ""

Write-Host "🚀 Starting in 5 seconds..." -ForegroundColor Yellow
Write-Host "   Terminal 1: Will watch metrics (this window)" -ForegroundColor White
Write-Host "   Terminal 2: Will run load test (new window)" -ForegroundColor White
Write-Host ""
Start-Sleep -Seconds 5

# Start load test in new terminal
Write-Host "▶️  Starting load test..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
Write-Host '🔥 Load Test Running' -ForegroundColor Red
Write-Host '50 users for 5 minutes' -ForegroundColor Yellow
Write-Host ''
cd '$PWD\load-testing'
python -m locust -f src/k8s/locustfile_constant_k8s.py --headless --users 50 --spawn-rate 10 --run-time 300s --html ../results/k8s_load_test_report.html
Write-Host ''
Write-Host 'Load test complete! Check results/k8s_load_test_report.html' -ForegroundColor Green
Write-Host 'Press any key to close...'
`$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
"@

Start-Sleep -Seconds 3

# Watch metrics in this terminal
Write-Host ""
Write-Host "👀 Watching metrics (updates every few seconds)..." -ForegroundColor Cyan
Write-Host "Watch CPU and Memory increase!" -ForegroundColor Yellow
Write-Host ""

kubectl top pods -n sock-shop --watch
