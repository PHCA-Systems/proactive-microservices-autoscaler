#!/usr/bin/env pwsh
# Quick 5-minute test to verify RPS values and ML predictions

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("proactive", "reactive")]
    [string]$Condition = "proactive"
)

Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "QUICK TEST: $Condition condition (5 minutes)"
Write-Host "=" -NoNewline; Write-Host "="*79

# Configuration
$NAMESPACE = "sock-shop"
$LOCUST_VM_IP = "35.222.116.125"
$LOCUST_SSH_USER = "User"
$LOCUST_SSH_KEY = "$env:USERPROFILE\.ssh\google_compute_engine"
$SOCK_SHOP_IP = "104.154.246.88"

# Step 1: Configure condition
Write-Host "`nStep 1: Configuring $Condition condition..."

if ($Condition -eq "proactive") {
    Write-Host "  Deleting HPAs..."
    kubectl delete hpa --all -n $NAMESPACE --ignore-not-found=true
    
    Write-Host "  Starting scaling-controller..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        scale deployment scaling-controller -n kafka --replicas=1
    
    Start-Sleep -Seconds 15
    Write-Host "  Proactive system active"
} else {
    Write-Host "  Stopping scaling-controller..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        scale deployment scaling-controller -n kafka --replicas=0
    
    Write-Host "  Applying HPAs..."
    kubectl apply -f ../k8s/hpa-baseline.yaml
    
    Start-Sleep -Seconds 15
    Write-Host "  Reactive HPA active"
}

# Step 2: Reset cluster
Write-Host "`nStep 2: Resetting all services to 1 replica..."
$services = @("front-end", "carts", "orders", "catalogue", "user", "payment", "shipping")
foreach ($svc in $services) {
    kubectl scale deployment $svc -n $NAMESPACE --replicas=1 | Out-Null
}
Write-Host "  Waiting 60 seconds for stabilization..."
Start-Sleep -Seconds 60

# Step 3: Start load test
Write-Host "`nStep 3: Starting Locust load test (constant pattern, 5 minutes)..."

$remoteCmd = @"
source ~/locust-venv/bin/activate && \
LOCUST_RUN_TIME_MINUTES=5 \
locust -f ~/locustfile_constant.py --headless --run-time 5m \
--host http://$SOCK_SHOP_IP 2>&1
"@

$sshCmd = @(
    "ssh",
    "-i", $LOCUST_SSH_KEY,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "$LOCUST_SSH_USER@$LOCUST_VM_IP",
    $remoteCmd
)

Write-Host "  Locust starting on VM..."
$locustProc = Start-Process -FilePath "ssh" -ArgumentList $sshCmd[1..($sshCmd.Length-1)] -NoNewWindow -PassThru

# Step 4: Monitor ML inference logs
Write-Host "`nStep 4: Monitoring ML inference logs (press Ctrl+C to stop)..."
Write-Host "  Waiting 30 seconds for first metrics..."
Start-Sleep -Seconds 30

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "ML INFERENCE LOGS (showing RPS values and predictions)"
Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host ""

# Tail logs from Random Forest model
kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
    logs -n kafka deployment/ml-inference-rf --tail=100 -f

# Cleanup
Write-Host "`n`nStopping Locust..."
if ($locustProc -and !$locustProc.HasExited) {
    Stop-Process -Id $locustProc.Id -Force
}

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "TEST COMPLETE"
Write-Host "=" -NoNewline; Write-Host "="*79

Write-Host "`nTo check other model logs:"
Write-Host "  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-xgb --tail=50"
Write-Host "  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-lr --tail=50"

Write-Host "`nTo check authoritative scaler decisions:"
Write-Host "  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/authoritative-scaler --tail=50"
