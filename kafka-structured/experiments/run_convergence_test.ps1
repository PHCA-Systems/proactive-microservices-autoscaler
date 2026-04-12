#!/usr/bin/env pwsh
# 20-Minute Convergence Test
# Tests if autoscaling system reaches steady state with minimal violations

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("proactive", "reactive")]
    [string]$Condition,
    
    [Parameter(Mandatory=$false)]
    [int]$RunId = [int](Get-Date -UFormat %s)
)

$ErrorActionPreference = "Continue"

# Configuration
$NAMESPACE = "sock-shop"
$LOCUST_VM_IP = "35.222.116.125"
$LOCUST_SSH_USER = "User"
$LOCUST_SSH_KEY = "$env:USERPROFILE\.ssh\google_compute_engine"
$SOCK_SHOP_IP = "104.154.246.88"
$PROMETHEUS_URL = "http://34.170.213.190:9090"
$SLO_THRESHOLD_MS = 36.0
$POLL_INTERVAL_S = 30
$TEST_DURATION_MIN = 20
$N_INTERVALS = 40  # 20 min / 30s = 40 snapshots

$MONITORED_SERVICES = @("front-end", "carts", "orders", "catalogue", "user", "payment", "shipping")

Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "20-MINUTE CONVERGENCE TEST: $Condition"
Write-Host "Run ID: $RunId"
Write-Host "=" -NoNewline; Write-Host "="*79

# Step 1: Configure condition
Write-Host "`nStep 1: Configuring $Condition condition..."

if ($Condition -eq "proactive") {
    Write-Host "  Deleting HPAs..."
    kubectl delete hpa --all -n $NAMESPACE --ignore-not-found=true | Out-Null
    
    Write-Host "  Starting scaling-controller..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        scale deployment scaling-controller -n kafka --replicas=1 | Out-Null
    
    Start-Sleep -Seconds 15
    Write-Host "  Proactive system active"
} else {
    Write-Host "  Stopping scaling-controller..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        scale deployment scaling-controller -n kafka --replicas=0 | Out-Null
    
    Write-Host "  Applying HPAs..."
    kubectl apply -f ../k8s/hpa-baseline.yaml | Out-Null
    
    Start-Sleep -Seconds 15
    Write-Host "  Reactive HPA active"
}

# Step 2: Reset cluster
Write-Host "`nStep 2: Resetting all services to 1 replica..."
foreach ($svc in $MONITORED_SERVICES) {
    kubectl scale deployment $svc -n $NAMESPACE --replicas=1 | Out-Null
}
Write-Host "  Waiting 120 seconds for stabilization..."
Start-Sleep -Seconds 120

# Step 3: Start load test
Write-Host "`nStep 3: Starting Locust load test (150 users, 20 minutes)..."

$remoteCmd = @"
source ~/locust-venv/bin/activate && \
LOCUST_RUN_TIME_MINUTES=20 \
locust -f ~/locustfile_constant.py --headless --run-time 20m \
--host http://$SOCK_SHOP_IP 2>&1
"@

$sshArgs = @(
    "-i", $LOCUST_SSH_KEY,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "$LOCUST_SSH_USER@$LOCUST_VM_IP",
    $remoteCmd
)

Write-Host "  Locust starting on VM..."
$locustProc = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -NoNewWindow -PassThru

# Step 4: Collect metrics
Write-Host "`nStep 4: Collecting metrics every 30 seconds (40 snapshots)..."
Write-Host "  Output: results/${Condition}_convergence_run${RunId}.jsonl"

$outputPath = "results/${Condition}_convergence_run${RunId}.jsonl"
New-Item -ItemType Directory -Force -Path "results" | Out-Null

$snapshots = @()

for ($i = 0; $i -lt $N_INTERVALS; $i++) {
    Start-Sleep -Seconds $POLL_INTERVAL_S
    
    $timestamp = Get-Date -Format "o"
    $snapshot = @{
        timestamp = $timestamp
        run_id = $RunId
        condition = $Condition
        pattern = "constant"
        interval_idx = $i
        services = @{}
    }
    
    # Collect metrics for each service
    foreach ($svc in $MONITORED_SERVICES) {
        # Get replica count
        try {
            $deployment = kubectl get deployment $svc -n $NAMESPACE -o json | ConvertFrom-Json
            $replicas = $deployment.spec.replicas
        } catch {
            $replicas = -1
        }
        
        # Query p95 latency from Prometheus
        $p95Query = "histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))"
        try {
            $response = Invoke-RestMethod -Uri "$PROMETHEUS_URL/api/v1/query" -Method Get -Body @{query=$p95Query} -TimeoutSec 5
            $p95 = 0.0
            foreach ($result in $response.data.result) {
                $metricSvc = $result.metric.service
                if (!$metricSvc) { $metricSvc = $result.metric.job }
                if ($metricSvc -eq "cart") { $metricSvc = "carts" }
                if ($metricSvc -eq "frontend") { $metricSvc = "front-end" }
                
                if ($metricSvc -eq $svc) {
                    $value = [double]$result.value[1]
                    if ($value -eq $value) {  # Not NaN
                        $p95 = $value * 1000.0  # Convert to ms
                        break
                    }
                }
            }
        } catch {
            $p95 = 0.0
        }
        
        # Query CPU
        $cpuQuery = "sum(rate(container_cpu_usage_seconds_total{namespace=`"$NAMESPACE`", pod=~`"$svc.*`"}[1m])) * 100"
        try {
            $response = Invoke-RestMethod -Uri "$PROMETHEUS_URL/api/v1/query" -Method Get -Body @{query=$cpuQuery} -TimeoutSec 5
            if ($response.data.result.Count -gt 0) {
                $cpu = [double]$response.data.result[0].value[1]
                if ($cpu -ne $cpu) { $cpu = 0.0 }  # Handle NaN
            } else {
                $cpu = 0.0
            }
        } catch {
            $cpu = 0.0
        }
        
        $sloViolated = $p95 -gt $SLO_THRESHOLD_MS
        
        $snapshot.services[$svc] = @{
            replicas = $replicas
            p95_ms = [math]::Round($p95, 2)
            cpu_pct = [math]::Round($cpu, 2)
            slo_violated = $sloViolated
        }
    }
    
    # Save snapshot
    $snapshots += $snapshot
    $snapshot | ConvertTo-Json -Compress | Out-File -Append -FilePath $outputPath
    
    # Calculate aggregate violation rate
    $violations = ($snapshot.services.Values | Where-Object { $_.slo_violated }).Count
    $violationPct = [math]::Round(($violations / $MONITORED_SERVICES.Count) * 100, 1)
    
    # Display progress
    $replicaStr = ($MONITORED_SERVICES | ForEach-Object { "$_=$($snapshot.services[$_].replicas)" }) -join " "
    Write-Host "  [$($i+1)/$N_INTERVALS] Violations: $violations/$($MONITORED_SERVICES.Count) ($violationPct%) | $replicaStr"
    
    # Check if Locust is still running
    if ($locustProc.HasExited) {
        Write-Host "  WARNING: Locust exited early at interval $($i+1)"
        break
    }
}

# Stop Locust
Write-Host "`nStopping Locust..."
if ($locustProc -and !$locustProc.HasExited) {
    Stop-Process -Id $locustProc.Id -Force -ErrorAction SilentlyContinue
}

# Wait for settle
Write-Host "Waiting 60 seconds for settle..."
Start-Sleep -Seconds 60

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "TEST COMPLETE"
Write-Host "=" -NoNewline; Write-Host "="*79

# Analysis
Write-Host "`nQuick Analysis:"
Write-Host "  Total snapshots: $($snapshots.Count)"

# Calculate violation rate over time
$earlyViolations = ($snapshots[0..9] | ForEach-Object { ($_.services.Values | Where-Object { $_.slo_violated }).Count }) | Measure-Object -Average
$midViolations = ($snapshots[10..29] | ForEach-Object { ($_.services.Values | Where-Object { $_.slo_violated }).Count }) | Measure-Object -Average
$lateViolations = ($snapshots[30..39] | ForEach-Object { ($_.services.Values | Where-Object { $_.slo_violated }).Count }) | Measure-Object -Average

Write-Host "  Early (0-5 min): $([math]::Round($earlyViolations.Average / $MONITORED_SERVICES.Count * 100, 1))% violations"
Write-Host "  Mid (5-15 min): $([math]::Round($midViolations.Average / $MONITORED_SERVICES.Count * 100, 1))% violations"
Write-Host "  Late (15-20 min): $([math]::Round($lateViolations.Average / $MONITORED_SERVICES.Count * 100, 1))% violations"

# Final replica counts
Write-Host "`n  Final replica counts:"
foreach ($svc in $MONITORED_SERVICES) {
    $finalReplicas = $snapshots[-1].services[$svc].replicas
    Write-Host "    $svc : $finalReplicas"
}

Write-Host "`nResults saved to: $outputPath"
