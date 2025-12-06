# PowerShell script to install dependencies on Windows
# Handles the geventhttpclient compilation issue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Python Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Upgrade pip, setuptools, wheel first
Write-Host "Upgrading pip, setuptools, wheel..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel

Write-Host ""
Write-Host "Attempting to install geventhttpclient with pre-built wheels..." -ForegroundColor Yellow
$geventResult = python -m pip install --only-binary :all: geventhttpclient 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ geventhttpclient installed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠ Pre-built wheels not available for geventhttpclient" -ForegroundColor Yellow
    Write-Host "This package requires Microsoft C++ Build Tools to compile." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "1. Install Microsoft C++ Build Tools:" -ForegroundColor White
    Write-Host "   https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Try installing anyway (may fail):" -ForegroundColor White
    Write-Host "   python -m pip install geventhttpclient" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Use Docker for Locust instead (recommended for production)" -ForegroundColor White
    Write-Host ""
    
    $continue = Read-Host "Continue with installation anyway? (y/n)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        Write-Host "Installation cancelled." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Attempting to install geventhttpclient (this may take a while)..." -ForegroundColor Yellow
    python -m pip install geventhttpclient
}

Write-Host ""
Write-Host "Installing remaining packages (locust, pandas, numpy, requests)..." -ForegroundColor Yellow
python -m pip install locust pandas numpy requests

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verifying installation..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$packages = @("locust", "pandas", "numpy", "requests")
$allInstalled = $true

foreach ($pkg in $packages) {
    try {
        python -c "import $pkg; print('✓ $pkg installed')" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ $pkg not installed correctly" -ForegroundColor Red
            $allInstalled = $false
        }
    } catch {
        Write-Host "✗ $pkg not installed correctly" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""
if ($allInstalled) {
    Write-Host "✓ All packages installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run:" -ForegroundColor Cyan
    Write-Host "  python loadgen/example_usage.py" -ForegroundColor White
} else {
    Write-Host "⚠ Some packages failed to install." -ForegroundColor Yellow
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
}

