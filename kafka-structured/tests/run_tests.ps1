#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run Kafka Pipeline Integration Tests

.DESCRIPTION
    This script starts Kafka infrastructure and runs integration tests
    for Task 1: Verify existing Kafka pipeline components

.PARAMETER SkipKafkaStart
    Skip starting Kafka (use if Kafka is already running)

.PARAMETER KafkaHost
    Kafka bootstrap server address (default: localhost:9092)

.EXAMPLE
    .\run_tests.ps1
    Start Kafka and run tests

.EXAMPLE
    .\run_tests.ps1 -SkipKafkaStart
    Run tests with existing Kafka instance
#>

param(
    [switch]$SkipKafkaStart,
    [string]$KafkaHost = "localhost:9092"
)

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "KAFKA PIPELINE INTEGRATION TEST RUNNER" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
if (-not $SkipKafkaStart) {
    Write-Host "[INFO] Checking Docker availability..." -ForegroundColor Yellow
    
    try {
        $dockerVersion = docker --version
        Write-Host "[OK] Docker is available: $dockerVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Docker is not available or not running" -ForegroundColor Red
        Write-Host "[INFO] Please start Docker Desktop or use -SkipKafkaStart if Kafka is already running" -ForegroundColor Yellow
        exit 1
    }
    
    # Check if Kafka is already running
    Write-Host "[INFO] Checking if Kafka is already running..." -ForegroundColor Yellow
    $kafkaRunning = docker ps --filter "name=kafka" --format "{{.Names}}" 2>$null
    
    if ($kafkaRunning -match "kafka") {
        Write-Host "[OK] Kafka is already running" -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] Starting Kafka infrastructure..." -ForegroundColor Yellow
        
        # Navigate to kafka-structured directory
        $scriptDir = Split-Path -Parent $PSCommandPath
        $kafkaDir = Split-Path -Parent $scriptDir
        
        Push-Location $kafkaDir
        
        try {
            # Start Zookeeper and Kafka
            Write-Host "[INFO] Starting Zookeeper and Kafka containers..." -ForegroundColor Yellow
            docker-compose -f docker-compose.ml.yml up -d zookeeper kafka
            
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to start Kafka containers"
            }
            
            Write-Host "[OK] Kafka containers started" -ForegroundColor Green
            
            # Wait for Kafka to be ready
            Write-Host "[INFO] Waiting for Kafka to be ready (30 seconds)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
            
            Write-Host "[OK] Kafka should be ready" -ForegroundColor Green
        }
        finally {
            Pop-Location
        }
    }
}
else {
    Write-Host "[INFO] Skipping Kafka startup (using existing instance at $KafkaHost)" -ForegroundColor Yellow
}

# Check Python availability
Write-Host ""
Write-Host "[INFO] Checking Python availability..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python is available: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Python is not available" -ForegroundColor Red
    Write-Host "[INFO] Please install Python 3.8 or higher" -ForegroundColor Yellow
    exit 1
}

# Check if kafka-python is installed
Write-Host "[INFO] Checking kafka-python package..." -ForegroundColor Yellow

$kafkaPythonInstalled = python -c "import kafka; print('installed')" 2>$null

if ($kafkaPythonInstalled -match "installed") {
    Write-Host "[OK] kafka-python is installed" -ForegroundColor Green
}
else {
    Write-Host "[WARN] kafka-python is not installed" -ForegroundColor Yellow
    Write-Host "[INFO] Installing kafka-python..." -ForegroundColor Yellow
    
    $scriptDir = Split-Path -Parent $PSCommandPath
    pip install -r "$scriptDir/requirements.txt"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install kafka-python" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[OK] kafka-python installed" -ForegroundColor Green
}

# Run tests
Write-Host ""
Write-Host "[INFO] Running integration tests..." -ForegroundColor Yellow
Write-Host ""

$scriptDir = Split-Path -Parent $PSCommandPath
$testScript = Join-Path $scriptDir "test_kafka_pipeline.py"

# Update Kafka host in test script if needed
if ($KafkaHost -ne "localhost:9092") {
    Write-Host "[INFO] Using custom Kafka host: $KafkaHost" -ForegroundColor Yellow
    $env:KAFKA_BOOTSTRAP = $KafkaHost
}

python $testScript

$testExitCode = $LASTEXITCODE

Write-Host ""
if ($testExitCode -eq 0) {
    Write-Host "[SUCCESS] All tests passed!" -ForegroundColor Green
}
else {
    Write-Host "[FAILURE] Some tests failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan

exit $testExitCode
