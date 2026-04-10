# run_overnight.ps1
# Overnight data collection script.
#
# Phase A: 3 more runs each of ramp, spike, step  (~9 x 17min = ~2.5 hrs)
# Phase B: 4-hour mixed run (15 segments, exact local sequence)  (~4.2 hrs)
# Phase C: GKE shutdown
#
# Total: ~7 hours
# Usage: .\run_overnight.ps1

param(
    [int]$DurationMin  = 15,
    [int]$WarmupSec    = 60,
    [int]$WinddownSec  = 60
)

#  Config 
$GCLOUD_BIN   = "C:\Users\User\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
$SOCK_SHOP_IP = "104.154.246.88"
$ZONE         = "us-central1-a"
$CLUSTER_NAME = "sock-shop-cluster"
$VM_NAME      = "locust-runner"
$SSH_KEY      = "$env:USERPROFILE\.ssh\google_compute_engine"
$SSH_USER     = "User"
$VM_IP        = "136.115.51.98"
$PYTHON       = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\venv\Scripts\python.exe"
$APP          = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\app.py"
$BASE_OUT     = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\output\experiments"
$MIXED_OUT    = "$PSScriptRoot\kafka-structured\services\metrics-aggregator\output\mixed_gke"
$LOG_FILE     = "$PSScriptRoot\overnight_log.txt"

# Exact local sequence: 15 segments = 240 minutes
$MIXED_SEQUENCE = @(
    @{ Pattern="ramp";     DurationMin=15 },
    @{ Pattern="constant"; DurationMin=20 },
    @{ Pattern="spike";    DurationMin=10 },
    @{ Pattern="step";     DurationMin=30 },
    @{ Pattern="ramp";     DurationMin=25 },
    @{ Pattern="constant"; DurationMin=15 },
    @{ Pattern="spike";    DurationMin=5  },
    @{ Pattern="step";     DurationMin=20 },
    @{ Pattern="ramp";     DurationMin=10 },
    @{ Pattern="constant"; DurationMin=30 },
    @{ Pattern="spike";    DurationMin=15 },
    @{ Pattern="step";     DurationMin=10 },
    @{ Pattern="ramp";     DurationMin=20 },
    @{ Pattern="constant"; DurationMin=10 },
    @{ Pattern="spike";    DurationMin=15 }
)

# Initial user counts per pattern (matches local run_experiment.py)
$PATTERN_USERS = @{
    constant = "--users 50 --spawn-rate 5"
    ramp     = "--users 10 --spawn-rate 2"
    spike    = "--users 10 --spawn-rate 2"
    step     = "--users 50 --spawn-rate 5"
}

$env:PATH += ";$GCLOUD_BIN"
$env:USE_GKE_GCLOUD_AUTH_PLUGIN = "True"

#  Logging 
function Log {
    param([string]$Msg, [string]$Color = "White")
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Msg"
    Write-Host $line -ForegroundColor $Color
    Add-Content -Path $LOG_FILE -Value $line
}

function Log-Section {
    param([string]$Msg)
    Log ("=" * 65) "DarkGray"
    Log "  $Msg" "Cyan"
    Log ("=" * 65) "DarkGray"
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
    Log "  [$Label] complete"
}

#  SSH helper 
function Invoke-VM {
    param([string]$Command)
    ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${VM_IP}" $Command
}

#  Start port-forward 
function Start-PortForward {
    $job = Start-Job -ScriptBlock {
        $env:USE_GKE_GCLOUD_AUTH_PLUGIN = "True"
        $env:PATH = "C:\Users\User\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin;" + $env:PATH
        & "C:\Program Files\Docker\Docker\resources\bin\kubectl.exe" port-forward -n monitoring svc/prometheus-server 9090:80
    }
    Start-Sleep -Seconds 6
    if ((Get-Job $job.Id).State -ne "Running") {
        $out = Receive-Job $job -ErrorAction SilentlyContinue
        Log "ERROR: Port-forward failed. Job output: $out" "Red"
        Remove-Job $job
        return $null
    }
    return $job
}

#  Start aggregator 
function Start-Aggregator {
    param([string]$OutDir)
    $py  = (Resolve-Path $PYTHON).Path
    $app = (Resolve-Path $APP).Path
    $job = Start-Job -ScriptBlock {
        param($py, $app, $out)
        $env:MODE              = "development"
        $env:PROMETHEUS_URL    = "http://localhost:9090"
        $env:POLL_INTERVAL_SEC = "30"
        $env:OUTPUT_DIR        = $out
        & $py $app
    } -ArgumentList $py, $app, $OutDir
    Start-Sleep -Seconds 22
    if ((Get-Job $job.Id).State -ne "Running") {
        Log "ERROR: Aggregator failed to start" "Red"
        Remove-Job $job
        return $null
    }
    return $job
}

#  Run locust on VM (blocking, separate window) 
function Invoke-Locust {
    param([string]$Pattern, [int]$DurMin, [string]$ExtraArgs)
    $locustFile = "locustfile_$Pattern.py"
    $cmd = "source ~/locust-venv/bin/activate && LOCUST_RUN_TIME_MINUTES=$DurMin locust -f ~/$locustFile --headless --run-time ${DurMin}m --host http://$SOCK_SHOP_IP $ExtraArgs 2>&1"
    $sshArgs = "-Command `"ssh -i '$SSH_KEY' -o StrictHostKeyChecking=no -o BatchMode=yes '${SSH_USER}@${VM_IP}' '$cmd'; Write-Host 'LOCUST_DONE'`""
    $proc = Start-Process powershell -ArgumentList $sshArgs -PassThru
    $timeoutMs = ($DurMin * 60 + 180) * 1000
    $exited = $proc.WaitForExit($timeoutMs)
    if (-not $exited) {
        Log "WARNING: Locust window timed out for $Pattern ${DurMin}m  killing" "Red"
        $proc.Kill()
        return $false
    }
    return $true
}

#  Prerequisites check 
function Assert-Prerequisites {
    Log "Checking prerequisites..." "Yellow"

    if (-not (Test-Path $PYTHON)) { Log "ERROR: Python not found: $PYTHON" "Red"; exit 1 }
    if (-not (Test-Path $APP))    { Log "ERROR: app.py not found: $APP" "Red"; exit 1 }
    if (-not (Test-Path $SSH_KEY)){ Log "ERROR: SSH key not found: $SSH_KEY" "Red"; exit 1 }

    $ping = Invoke-VM "echo ALIVE"
    if ($ping -notmatch "ALIVE") { Log "ERROR: Cannot reach VM at $VM_IP" "Red"; exit 1 }

    $files = Invoke-VM "ls ~/locustfile_ramp.py ~/locustfile_spike.py ~/locustfile_step.py ~/locustfile_constant.py 2>&1"
    if ($files -match "No such file") { Log "ERROR: Missing locust files on VM" "Red"; exit 1 }

    Log "Prerequisites OK" "Green"
}

#  GKE Shutdown 
function Invoke-GKEShutdown {
    Log-Section "PHASE C: GKE SHUTDOWN"
    Get-Job | Stop-Job; Get-Job | Remove-Job
    Stop-Process -Name kubectl -ErrorAction SilentlyContinue
    Stop-Process -Name python  -ErrorAction SilentlyContinue

    Log "Resizing cluster to 0 nodes..." "Yellow"
    gcloud container clusters resize $CLUSTER_NAME --num-nodes=0 --zone=$ZONE --quiet 2>&1 |
        ForEach-Object { Log $_ }

    Log "Stopping Locust VM..." "Yellow"
    gcloud compute instances stop $VM_NAME --zone=$ZONE --quiet 2>&1 |
        ForEach-Object { Log $_ }

    Log "Shutdown complete." "Green"
}

# 
# MAIN
# ===========================================================================
$startTime = Get-Date
"" | Set-Content $LOG_FILE

Log-Section "OVERNIGHT EXPERIMENT SUITE"
Log "Start      : $(Get-Date -Format 'HH:mm:ss')"
Log "Phase A    : ramp x3, spike x3, step x3  (~2.5 hrs)"
Log "Phase B    : mixed 4-hour run, 15 segments (~4.2 hrs)"
Log "Phase C    : GKE shutdown"
Log "Est. total : ~7 hrs"

Assert-Prerequisites

$summary = [System.Collections.Generic.List[hashtable]]::new()

# 
# PHASE A: Additional pattern runs
# 
Log-Section "PHASE A: ADDITIONAL PATTERN RUNS"

$phaseA = @(
    @{ Pattern="ramp";  Run="run_5" }, @{ Pattern="ramp";  Run="run_6" }, @{ Pattern="ramp";  Run="run_7" },
    @{ Pattern="spike"; Run="run_5" }, @{ Pattern="spike"; Run="run_6" }, @{ Pattern="spike"; Run="run_7" },
    @{ Pattern="step";  Run="run_5" }, @{ Pattern="step";  Run="run_6" }, @{ Pattern="step";  Run="run_7" }
)

foreach ($exp in $phaseA) {
    $pattern = $exp.Pattern
    $run     = $exp.Run
    $label   = "$pattern/$run"
    $outDir  = "$BASE_OUT\$pattern\$run"
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null

    Log-Section "$label  |  $(Get-Date -Format 'HH:mm')"

    $pfJob  = Start-PortForward
    if ($null -eq $pfJob) { $summary.Add(@{Label=$label;OK=$false}); continue }

    $aggJob = Start-Aggregator -OutDir $outDir
    if ($null -eq $aggJob) {
        Stop-Job $pfJob; Remove-Job $pfJob
        $summary.Add(@{Label=$label;OK=$false}); continue
    }

    Log "[3/5] Warmup ${WarmupSec}s" "Yellow"
    Wait-WithCountdown -Seconds $WarmupSec -Label "Warmup"

    Log "[4/5] Locust $pattern ${DurationMin}m" "Yellow"
    $loadStart = Get-Date
    $ok = Invoke-Locust -Pattern $pattern -DurMin $DurationMin -ExtraArgs $PATTERN_USERS[$pattern]
    $loadMin = [math]::Round(((Get-Date) - $loadStart).TotalMinutes, 1)
    Log "      Locust done (${loadMin}m actual)" $(if ($ok) {"Green"} else {"Red"})

    Log "[5/5] Winddown ${WinddownSec}s" "Yellow"
    Wait-WithCountdown -Seconds $WinddownSec -Label "Winddown"

    Stop-Job $aggJob; Remove-Job $aggJob
    Stop-Job $pfJob;  Remove-Job $pfJob
    Start-Sleep -Seconds 6

    $rows = 0
    $csv  = "$outDir\sockshop_metrics.csv"
    if (Test-Path $csv) { $rows = (Get-Content $csv | Measure-Object -Line).Lines - 1 }
    $status = if ($rows -gt 50 -and $ok) { "OK" } else { "SUSPECT" }
    Log "DONE: $label  $rows rows [$status]" $(if ($status -eq "OK") {"Green"} else {"Red"})
    $summary.Add(@{ Label=$label; OK=($status -eq "OK") })

    Log "Cooling down 30s..." "DarkGray"
    Start-Sleep -Seconds 30
}

# 
# PHASE B: Mixed 4-hour run (15 segments, one aggregator for full duration)
# 
Log-Section "PHASE B: MIXED 4-HOUR RUN (15 segments)"

$totalMixedMin = ($MIXED_SEQUENCE | Measure-Object -Property DurationMin -Sum).Sum
Log "Sequence: $($MIXED_SEQUENCE.Count) segments, $totalMixedMin minutes total"
for ($i = 0; $i -lt $MIXED_SEQUENCE.Count; $i++) {
    $s = $MIXED_SEQUENCE[$i]
    Log "  $($i+1). $($s.Pattern.PadRight(10)) $($s.DurationMin)m"
}

New-Item -ItemType Directory -Path $MIXED_OUT -Force | Out-Null

# Start port-forward once for the full mixed run
$pfJob = Start-PortForward
if ($null -eq $pfJob) {
    Log "ERROR: Cannot start port-forward for mixed run  skipping Phase B" "Red"
    $summary.Add(@{ Label="mixed/run_1"; OK=$false })
} else {
    # Start aggregator once for the full 4 hours
    $aggJob = Start-Aggregator -OutDir $MIXED_OUT
    if ($null -eq $aggJob) {
        Log "ERROR: Cannot start aggregator for mixed run  skipping Phase B" "Red"
        Stop-Job $pfJob; Remove-Job $pfJob
        $summary.Add(@{ Label="mixed/run_1"; OK=$false })
    } else {
        # Warmup before first segment
        Log "Warmup ${WarmupSec}s before first segment" "Yellow"
        Wait-WithCountdown -Seconds $WarmupSec -Label "Warmup"

        $mixedOk = $true
        $mixedStart = Get-Date

        for ($i = 0; $i -lt $MIXED_SEQUENCE.Count; $i++) {
            $seg     = $MIXED_SEQUENCE[$i]
            $segNum  = $i + 1
            $pattern = $seg.Pattern
            $durMin  = $seg.DurationMin
            $elapsed = [math]::Round(((Get-Date) - $mixedStart).TotalMinutes, 1)
            $remain  = $totalMixedMin - $elapsed

            Log "Segment $segNum/$($MIXED_SEQUENCE.Count): $pattern ${durMin}m  |  elapsed=${elapsed}m remaining=${remain}m" "Yellow"

            $loadStart = Get-Date
            $ok = Invoke-Locust -Pattern $pattern -DurMin $durMin -ExtraArgs $PATTERN_USERS[$pattern]
            $loadMin = [math]::Round(((Get-Date) - $loadStart).TotalMinutes, 1)

            if (-not $ok) {
                Log "WARNING: Segment $segNum ($pattern) may not have completed fully (${loadMin}m)" "Red"
                $mixedOk = $false
            } else {
                Log "  Segment $segNum done (${loadMin}m)" "Green"
            }

            # 5-second gap between segments (matches local pipeline)
            if ($segNum -lt $MIXED_SEQUENCE.Count) {
                Start-Sleep -Seconds 5
            }
        }

        # Winddown after last segment
        Log "Winddown ${WinddownSec}s after last segment" "Yellow"
        Wait-WithCountdown -Seconds $WinddownSec -Label "Winddown"

        Stop-Job $aggJob; Remove-Job $aggJob
        Stop-Job $pfJob;  Remove-Job $pfJob
        Start-Sleep -Seconds 6

        $rows = 0
        $csv  = "$MIXED_OUT\sockshop_metrics.csv"
        if (Test-Path $csv) { $rows = (Get-Content $csv | Measure-Object -Line).Lines - 1 }
        $expectedRows = $totalMixedMin * 2 * 7  # 2 polls/min x 7 services
        $status = if ($rows -gt ($expectedRows * 0.8) -and $mixedOk) { "OK" } else { "SUSPECT" }
        Log "DONE: mixed/run_1  $rows rows (expected ~$expectedRows) [$status]" $(if ($status -eq "OK") {"Green"} else {"Red"})
        $summary.Add(@{ Label="mixed/run_1"; OK=($status -eq "OK") })
    }
}

# 
# PHASE C: Shutdown
# 
Invoke-GKEShutdown

# 
# Summary
# 
$totalMin = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
Log-Section "ALL DONE  ${totalMin}m total"
foreach ($s in $summary) {
    $c = if ($s.OK) { "Green" } else { "Red" }
    Log ("  " + $s.Label.PadRight(22) + $(if ($s.OK) {"OK"} else {"FAILED"})) $c
}
Log ""
Log "Log file: $LOG_FILE"

