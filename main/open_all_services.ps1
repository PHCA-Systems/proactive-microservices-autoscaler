# Open all monitoring services in separate terminals
Write-Host "Opening Grafana..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Grafana - Login: admin/admin' -ForegroundColor Yellow; minikube service grafana -n monitoring"

Start-Sleep -Seconds 2

Write-Host "Opening Prometheus..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Prometheus Query Interface' -ForegroundColor Yellow; minikube service prometheus -n monitoring"

Start-Sleep -Seconds 2

Write-Host "Opening Sock Shop..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Sock Shop Application' -ForegroundColor Yellow; minikube service front-end -n sock-shop"

Write-Host ""
Write-Host "All services opened! Check the new terminal windows." -ForegroundColor Cyan
Write-Host "Next: Run .\run_k8s_load_test.ps1 in a new terminal" -ForegroundColor Yellow
