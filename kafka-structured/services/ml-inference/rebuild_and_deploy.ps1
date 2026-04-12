#!/usr/bin/env pwsh
# Rebuild and deploy ML inference services with debug logging

Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "REBUILDING ML INFERENCE SERVICES WITH DEBUG LOGGING"
Write-Host "=" -NoNewline; Write-Host "="*79

# Build Docker image using Google Cloud Build (no local Docker needed)
Write-Host "`nStep 1: Building Docker image with Cloud Build..."
gcloud builds submit --tag gcr.io/grad-phca/ml-inference:debug .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cloud Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "`nImage built and pushed to gcr.io/grad-phca/ml-inference:debug"

# Update deployments to use new image
Write-Host "`nStep 2: Updating ML inference deployments..."

$models = @("xgb", "rf", "lr")
foreach ($model in $models) {
    Write-Host "  Updating ml-inference-$model..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        set image deployment/ml-inference-$model `
        ml-inference=gcr.io/grad-phca/ml-inference:debug `
        -n kafka
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: Failed to update ml-inference-$model" -ForegroundColor Yellow
    }
}

# Wait for rollout
Write-Host "`nStep 3: Waiting for rollout to complete..."
foreach ($model in $models) {
    Write-Host "  Waiting for ml-inference-$model..."
    kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster `
        rollout status deployment/ml-inference-$model `
        -n kafka `
        --timeout=120s
}

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline; Write-Host "="*79
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline; Write-Host "="*79

Write-Host "`nTo view logs with RPS debugging:"
Write-Host "  kubectl --context=gke_grad-phca_us-central1-a_pipeline-cluster logs -n kafka deployment/ml-inference-rf --tail=50 -f"
