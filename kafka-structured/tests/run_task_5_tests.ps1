#!/usr/bin/env pwsh
# Task 5 Checkpoint Test Runner

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task 5 Checkpoint Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the tests directory
if (-not (Test-Path "test_task_5_quick.py")) {
    Write-Host "Error: Must run from kafka-structured/tests directory" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
$venvPath = "../services/metrics-aggregator/venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Error: Virtual environment not found at $venvPath" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath/Scripts/Activate.ps1"

# Check if Kafka is running
Write-Host "Checking Kafka connection..." -ForegroundColor Yellow
$kafkaBootstrap = $env:KAFKA_BOOTSTRAP_SERVERS
if (-not $kafkaBootstrap) {
    $kafkaBootstrap = "localhost:9092"
    $env:KAFKA_BOOTSTRAP_SERVERS = $kafkaBootstrap
}
Write-Host "Using Kafka bootstrap: $kafkaBootstrap" -ForegroundColor Green

# Check if scaling controller is running
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: Ensure scaling controller is running!" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The scaling controller must be running for these tests to work."
Write-Host "Start it with: python ../services/scaling-controller/controller.py"
Write-Host ""
$continue = Read-Host "Is the scaling controller running? (y/n)"
if ($continue -ne "y") {
    Write-Host "Please start the scaling controller first." -ForegroundColor Red
    exit 1
}

# Ask which test to run
Write-Host ""
Write-Host "Select test to run:" -ForegroundColor Cyan
Write-Host "1. Quick tests (~30 seconds)" -ForegroundColor Green
Write-Host "2. Full checkpoint tests (~7 minutes, includes scale-down)" -ForegroundColor Yellow
Write-Host "3. Both (quick first, then full)" -ForegroundColor Magenta
Write-Host ""
$choice = Read-Host "Enter choice (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Running quick tests..." -ForegroundColor Green
        python test_task_5_quick.py
        $exitCode = $LASTEXITCODE
    }
    "2" {
        Write-Host ""
        Write-Host "Running full checkpoint tests..." -ForegroundColor Yellow
        Write-Host "This will take approximately 7 minutes..." -ForegroundColor Yellow
        python test_task_5_checkpoint.py
        $exitCode = $LASTEXITCODE
    }
    "3" {
        Write-Host ""
        Write-Host "Running quick tests first..." -ForegroundColor Green
        python test_task_5_quick.py
        $quickExitCode = $LASTEXITCODE
        
        if ($quickExitCode -eq 0) {
            Write-Host ""
            Write-Host "Quick tests passed! Proceeding to full tests..." -ForegroundColor Green
            Write-Host "This will take approximately 7 minutes..." -ForegroundColor Yellow
            python test_task_5_checkpoint.py
            $exitCode = $LASTEXITCODE
        } else {
            Write-Host ""
            Write-Host "Quick tests failed. Skipping full tests." -ForegroundColor Red
            $exitCode = $quickExitCode
        }
    }
    default {
        Write-Host "Invalid choice. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "Tests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Tests failed with exit code: $exitCode" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

exit $exitCode
