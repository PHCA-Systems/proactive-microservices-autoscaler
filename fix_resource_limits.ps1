# Fix GKE Resource Limits to Match Data Collection Environment
# This increases CPU limits to prevent throttling and Locust timeouts

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Updating Sock Shop Resource Limits" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will increase CPU limits from 100-500m to 1000m"
Write-Host "to match the unlimited resources in Docker Compose"
Write-Host "data collection environment."
Write-Host ""

# Services to update (the 7 monitored services)
$services = @(
    "front-end",
    "carts",
    "orders",
    "catalogue",
    "user",
    "payment",
    "shipping"
)

$namespace = "sock-shop"

Write-Host "Services to update:"
foreach ($svc in $services) {
    Write-Host "  - $svc"
}
Write-Host ""

Read-Host "Press ENTER to continue (or Ctrl+C to cancel)"
Write-Host ""

# Update each service
foreach ($svc in $services) {
    Write-Host "Updating $svc..." -ForegroundColor Yellow
    
    # Patch the deployment with new resource limits
    $patch = @'
[
    {
        "op": "replace",
        "path": "/spec/template/spec/containers/0/resources",
        "value": {
            "limits": {
                "cpu": "1000m",
                "memory": "1Gi"
            },
            "requests": {
                "cpu": "100m",
                "memory": "200Mi"
            }
        }
    }
]
'@
    
    try {
        kubectl patch deployment $svc -n $namespace --type='json' -p $patch
        Write-Host "  ✓ $svc updated successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Failed to update $svc" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Waiting for pods to restart..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Wait for all deployments to be ready
foreach ($svc in $services) {
    Write-Host "Waiting for $svc..." -ForegroundColor Yellow
    kubectl rollout status deployment/$svc -n $namespace --timeout=5m
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✓ All services updated successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "New resource limits:"
Write-Host "  CPU limit:    1000m (1 full core)"
Write-Host "  Memory limit: 1Gi"
Write-Host "  CPU request:  100m"
Write-Host "  Memory request: 200Mi"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run validation test: python kafka-structured/experiments/run_single_test.py --condition reactive --pattern step --run-id 995"
Write-Host "  2. Check Locust failure rate (should be <5%)"
Write-Host "  3. If successful, run full experiment schedule"
Write-Host ""
