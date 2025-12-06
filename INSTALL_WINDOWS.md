# Windows Installation Guide

## Issue: geventhttpclient Build Error

On Windows, `geventhttpclient` requires Microsoft Visual C++ 14.0+ to compile.

## Solution Options

### Option 1: Install Microsoft C++ Build Tools (Recommended)

1. Download and install **Microsoft C++ Build Tools**:
   - Visit: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Or direct link: https://aka.ms/vs/17/release/vs_buildtools.exe

2. During installation, select:
   - **C++ build tools** workload
   - **Windows 10/11 SDK** (latest version)

3. After installation, restart your terminal and try again:
   ```powershell
   pip install -r requirements.txt
   ```

### Option 2: Use Pre-built Wheels (Easier)

Try installing with pre-built wheels first:

```powershell
pip install --only-binary :all: locust pandas numpy requests
```

If that doesn't work, try installing geventhttpclient separately:

```powershell
pip install geventhttpclient --only-binary :all:
pip install locust pandas numpy requests
```

### Option 3: Use Docker for Locust (Best for Production)

Run Locust in a Docker container to avoid Windows compilation issues:

```powershell
# Create a Dockerfile for Locust
# Or use the official Locust image
docker run -it --rm -v ${PWD}:/mnt/locust -p 8089:8089 locustio/locust -f /mnt/locust/loadgen/locustfile.py --host=http://host.docker.internal
```

### Option 4: Use Alternative HTTP Client

Modify Locust to use a different HTTP client (requires code changes - not recommended).

## Quick Fix Script

Create `install_deps.ps1`:

```powershell
# Try to install with pre-built wheels
Write-Host "Attempting to install with pre-built wheels..." -ForegroundColor Cyan
pip install --only-binary :all: geventhttpclient 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Success! Installing remaining packages..." -ForegroundColor Green
    pip install locust pandas numpy requests
} else {
    Write-Host "Pre-built wheels not available. You need to install Microsoft C++ Build Tools." -ForegroundColor Yellow
    Write-Host "Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Yellow
    Write-Host "Or try: pip install --upgrade pip setuptools wheel" -ForegroundColor Yellow
    pip install --upgrade pip setuptools wheel
    pip install locust pandas numpy requests
}
```

## Verify Installation

After installation, verify:

```powershell
python -c "import locust; print('Locust version:', locust.__version__)"
python -c "import pandas; print('Pandas installed')"
python -c "import numpy; print('NumPy installed')"
```

## Alternative: Use Conda

If you have Anaconda/Miniconda:

```powershell
conda install -c conda-forge locust pandas numpy requests
```

This often has pre-compiled packages that avoid the build issue.

