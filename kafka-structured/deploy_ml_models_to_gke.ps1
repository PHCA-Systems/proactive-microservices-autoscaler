# Deploy Updated ML Inference Service to GKE
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deploying ML Inference to GKE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$PROJECT_ID = "grad-phca"
$IMAGE_NAME = "ml-inference"
$IMAGE_TAG = "latest"
$FULL_IMAGE = "gcr.io/$PROJECT_ID/${IMAGE_NAME}:${IMAGE_TAG}"
$CONTEXT = "gke_grad-phca_us-central1-a_pipeline-cluster"

Write-Host "Image: $FULL_IMAGE"
Write-Host "Context: $CONTEXT"
Write-Host ""

# Step 1: Build the Docker image
Write-Host "Step 1: Building Docker image..." -ForegroundColor Green
Push-Location services/ml-inference

docker build -t $FULL_IMAGE .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Docker image built successfully" -ForegroundColor Green

# Step 2: Push to GCR
Write-Host "Step 2: Pushing image to GCR..." -ForegroundColor Green
docker push $FULL_IMAGE
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker push failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Image pushed successfully" -ForegroundColor Green

Pop-Location

# Step 3: Restart deployments
Write-Host "Step 3: Restarting ML inference deployments..." -ForegroundColor Green
$deployments = @("ml-inference-lr", "ml-inference-rf", "ml-inference-xgb")

foreach ($deployment in $deployments) {
    Write-Host "Restarting $deployment..."
    kubectl --context=$CONTEXT rollout restart deployment/$deployment -n kafka
}

# Step 4: Wait for rollout
Write-Host "Step 4: Waiting for deployments..." -ForegroundColor Green
foreach ($deployment in $deployments) {
    kubectl --context=$CONTEXT rollout status deployment/$deployment -n kafka --timeout=5m
}

Write-Host ""
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "Verify: kubectl --context=$CONTEXT logs -n kafka -l app=ml-inference-lr --tail=30"
