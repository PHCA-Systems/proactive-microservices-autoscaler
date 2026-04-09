# run_all_experiments.ps1
# Usage: .\run_all_experiments.ps1
# Override: .\run_all_experiments.ps1 -DurationMin 10 -WarmupSec 30

param(
    [int]$DurationMin = 15,
    [int]$WarmupSec   = 60,
    [int]$WinddownSec = 60
)

# Per-pattern run counts
$patternRuns = [ordered]@{
    constant = 4
}

# Skip only confirmed good runs
$skipRuns = @{}
$skipSpecific = @{
    constant = @(1, 2)
}

# Config
$GCLOUD_BIN   = "C:\Users\User\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
$SOCK_SHOP_IP = "104.154.246.88"
$ZONE         = "us-central1-a"
$VM_NAME      = "locust-runner"
$PYTHON       = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\venv\Scripts\python.exe"
$APP          = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\app.py"
$BASE_OUT     = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\output\experiments"

$extraLocustArgs = @{
    constant = "--users 50 --spawn-rate 5"
    ramp     = ""
    spike    = ""
    step     = ""
}

# SSH config — use system ssh.exe directly, bypasses gcloud's plink entirely
$SSH_KEY = "$env:USERPROFILE\.ssh\google_compute_engine"
$VM_IP   = "136.115.51.98"
$SSH_USER = "User"

function Invoke-VMCommand {
    param([string]$Command)
    ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o BatchMode=yes "${SSH_USER}@${VM_IP}" $Command
}

# ── Logging ───────────────────────────────────────────────────────────────────
function Log {
    param([string]$Msg, [string]$Color = "White")
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] $Msg" -ForegroundColor $Color
}

function Log-Section {
    param([string]$Msg)
    Write-Host ""
    Write-Host ("=" * 62) -ForegroundColor DarkGray
    Write-Host "  $Msg" -ForegroundColor Cyan
    Write-Host ("=" * 62) -ForegroundColor DarkGray
}

function Wait-WithCountdown {
    param([int]$Seconds, [string]$Label)
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        $left = [math]::Round(($end - (Get-Date)).TotalSeconds)
        Write-Host "`r  [$Label] ${left}s remaining...   " -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host "`r  [$Label] done.                    "
}

# ── ETA ───────────────────────────────────────────────────────────────────────
$secPerRun     = $WarmupSec + ($DurationMin * 60) + $WinddownSec + 30
$totalRuns     = ($patternRuns.Values | Measure-Object -Sum).Sum - ($skipSpecific.Values | ForEach-Object { $_.Count } | Measure-Object -Sum).Sum
$startTime     = Get-Date
$completedRuns = 0

function Get-ETA {
    if ($completedRuns -eq 0) {
        $remaining = $totalRuns * $secPerRun
    } else {
        $elapsed   = ((Get-Date) - $startTime).TotalSeconds
        $perRun    = $elapsed / $completedRuns
        $remaining = $perRun * ($totalRuns - $completedRuns)
    }
    $eta = (Get-Date).AddSeconds($remaining)
    return "ETA $($eta.ToString('HH:mm')) (~$([math]::Round($remaining / 60))m left)"
}

$summary = [System.Collections.Generic.List[hashtable]]::new()

# ── Banner ────────────────────────────────────────────────────────────────────
Log-Section "SOCK SHOP EXPERIMENT SUITE"
Log "Total runs    : $totalRuns"
Log "Per run       : ${WarmupSec}s warmup + ${DurationMin}m load + ${WinddownSec}s winddown"
Log "Est. total    : ~$([math]::Round($totalRuns * $secPerRun / 60))m"
Log "Output        : $BASE_OUT"
Log ""
foreach ($p in $patternRuns.Keys) {
    Log "  $($p.PadRight(10)) $($patternRuns[$p]) run(s)"
}

# ── Main loop ─────────────────────────────────────────────────────────────────
foreach ($pattern in $patternRuns.Keys) {
    $runs = $patternRuns[$pattern]

    for ($run = 1; $run -le $runs; $run++) {

        # Skip already-completed runs
        $skipUpTo = if ($skipRuns.ContainsKey($pattern)) { $skipRuns[$pattern] } else { 0 }
        if ($run -le $skipUpTo) {
            Log "Skipping $pattern/run_$run (already complete)" "DarkGray"
            $completedRuns++
            continue
        }

        # Skip specific runs that are already good
        if ($skipSpecific.ContainsKey($pattern) -and $skipSpecific[$pattern] -contains $run) {
            Log "Skipping $pattern/run_$run (already complete)" "DarkGray"
            $completedRuns++
            continue
        }

        $label    = "$pattern / run $run of $runs"
        $outDir   = "$BASE_OUT\$pattern\run_$run"
        $csvPath  = "$outDir\sockshop_metrics.csv"
        $runStart = Get-Date

        New-Item -ItemType Directory -Path $outDir -Force | Out-Null

        Log-Section "$label  |  $(Get-ETA)"
        Log "Output: $csvPath" "DarkGray"

        # 1. Port-forward
        Log "[1/5] Starting Prometheus port-forward..." "Yellow"
        $pfJob = Start-Job -ScriptBlock {
            $env:USE_GKE_GCLOUD_AUTH_PLUGIN = "True"
            $env:PATH += ";C:\Users\User\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
            kubectl port-forward -n monitoring svc/prometheus-server 9090:80
        }
        Start-Sleep -Seconds 5
        Log "      OK (job $($pfJob.Id))" "Green"

        # 2. Aggregator
        Log "[2/5] Starting metrics aggregator..." "Yellow"
        $resolvedPython = (Resolve-Path $PYTHON).Path
        $resolvedApp    = (Resolve-Path $APP).Path

        $aggJob = Start-Job -ScriptBlock {
            param($py, $app, $out)
            $env:MODE              = "development"
            $env:PROMETHEUS_URL    = "http://localhost:9090"
            $env:POLL_INTERVAL_SEC = "30"
            $env:OUTPUT_DIR        = $out
            & $py $app
        } -ArgumentList $resolvedPython, $resolvedApp, $outDir

        Start-Sleep -Seconds 20
        if ((Get-Job $aggJob.Id).State -ne "Running") {
            Log "ERROR: Aggregator failed to start - skipping run." "Red"
            Stop-Job $pfJob; Remove-Job $pfJob; Remove-Job $aggJob
            $summary.Add(@{ Label=$label; Status="FAILED"; Duration="N/A"; Rows="N/A" })
            continue
        }
        Log "      OK (job $($aggJob.Id))" "Green"

        # 3. Warmup
        Log "[3/5] Warmup - ${WarmupSec}s baseline (no load)" "Yellow"
        Wait-WithCountdown -Seconds $WarmupSec -Label "Warmup"

        # 4. Locust — runs in a separate visible window
        $runTime = "${DurationMin}m"
        $extra   = $extraLocustArgs[$pattern]

        Log "[4/5] Locust running - $pattern $runTime (see separate window)" "Yellow"
        $loadStart = Get-Date

        $locustScript = "source ~/locust-venv/bin/activate && LOCUST_RUN_TIME_MINUTES=$DurationMin locust -f ~/locustfile_$pattern.py --headless --run-time $runTime --host http://$SOCK_SHOP_IP $extra"
        $sshKey  = "$env:USERPROFILE\.ssh\google_compute_engine"
        $locustArgs = "-Command `"ssh -i '$sshKey' -o StrictHostKeyChecking=no -o BatchMode=yes 'User@136.115.51.98' '$locustScript'; Write-Host 'LOCUST DONE' -ForegroundColor Green`""
        $locustProc = Start-Process powershell -ArgumentList $locustArgs -PassThru

        $expectedMs = ($DurationMin * 60 + 120) * 1000
        $locustProc.WaitForExit($expectedMs + 120000) | Out-Null

        $loadMin = [math]::Round(((Get-Date) - $loadStart).TotalMinutes, 1)
        Log "      Locust done (${loadMin}m actual)" "Green"

        # 5. Winddown
        Log "[5/5] Winddown - ${WinddownSec}s recovery (no load)" "Yellow"
        Wait-WithCountdown -Seconds $WinddownSec -Label "Winddown"

        # Cleanup
        if (-not $locustProc.HasExited) { $locustProc.Kill() }
        Stop-Job $aggJob; Remove-Job $aggJob
        Stop-Job $pfJob;  Remove-Job $pfJob
        Start-Sleep -Seconds 5

        # Stats
        $rows = 0
        if (Test-Path $csvPath) {
            $rows = (Get-Content $csvPath | Measure-Object -Line).Lines - 1
        } else {
            Log "WARNING: CSV not found at $csvPath" "Red"
        }
        $elapsed = [math]::Round(((Get-Date) - $runStart).TotalMinutes, 1)
        $completedRuns++

        Log "DONE: $label - ${elapsed}m, $rows rows" "Green"
        $summary.Add(@{ Label=$label; Status="OK"; Duration="${elapsed}m"; Rows=$rows })

        $isLast = ($pattern -eq ($patternRuns.Keys | Select-Object -Last 1)) -and ($run -eq $runs)
        if (-not $isLast) {
            Log "Cooling down 30s before next run..." "DarkGray"
            Start-Sleep -Seconds 30
        }
    }
}

# ── Final summary ─────────────────────────────────────────────────────────────
$totalMin = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
Log-Section "ALL DONE - ${totalMin}m total"
Log ""
Log ("  {0,-38} {1,-8} {2,-10} {3}" -f "Run", "Status", "Duration", "Rows") "Cyan"
foreach ($s in $summary) {
    $c = if ($s.Status -eq "OK") { "Green" } else { "Red" }
    Log ("  {0,-38} {1,-8} {2,-10} {3}" -f $s.Label, $s.Status, $s.Duration, $s.Rows) $c
}
Log ""
Log "Output: $BASE_OUT"
