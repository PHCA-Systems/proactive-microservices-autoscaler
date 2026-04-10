#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run Task 4.2 Scale-Down Logic Tests

.DESCRIPTION
    This script runs unit tests for Task 4.2: Scale-Down Policy Implementation
    Tests verify that the scaling controller correctly implements scale-down logic
    with rolling window evaluation and all required conditions.

.EXAMPLE
    .\run_task_4_2_tests.ps1
    Run all Task 4.2 tests
#>

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "TASK 4.2 SCALE-DOWN LOGIC TEST RUNNER" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Check Python availability
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

# Run tests
Write-Host ""
Write-Host "[INFO] Running Task 4.2 scale-down logic tests..." -ForegroundColor Yellow
Write-Host ""

$scriptDir = Split-Path -Parent $PSCommandPath
$testScript = Join-Path $scriptDir "test_scale_down_logic.py"

python $testScript

$testExitCode = $LASTEXITCODE

Write-Host ""
if ($testExitCode -eq 0) {
    Write-Host "[SUCCESS] All Task 4.2 tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task 4.2 Implementation Summary:" -ForegroundColor Cyan
    Write-Host "  - Consumes from metrics topic" -ForegroundColor Green
    Write-Host "  - Maintains rolling window of 10 snapshots" -ForegroundColor Green
    Write-Host "  - Checks CPU threshold (30%)" -ForegroundColor Green
    Write-Host "  - Checks p95 latency threshold (0.7 x SLO)" -ForegroundColor Green
    Write-Host "  - Enforces MIN_REPLICAS bound" -ForegroundColor Green
    Write-Host "  - Enforces cooldown period" -ForegroundColor Green
    Write-Host "  - Decrements replicas by 1" -ForegroundColor Green
    Write-Host "  - Runs every 30 seconds" -ForegroundColor Green
}
else {
    Write-Host "[FAILURE] Some tests failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan

exit $testExitCode
