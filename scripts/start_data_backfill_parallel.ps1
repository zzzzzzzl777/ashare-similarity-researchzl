# Start parallel data backfill pipeline in background
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs\data_backfill_2020_2026"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$proc = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $scriptDir "run_data_backfill_parallel.py") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput (Join-Path $logDir "parallel_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "parallel_stderr.log") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Parallel backfill pipeline started!"
Write-Host "  PID: $($proc.Id)"
Write-Host "  Status: $logDir\status_parallel.json"
Write-Host "  Main log: $logDir\parallel.log"
Write-Host "  Paid API log: $logDir\paid_api_parallel.log"
Write-Host "  Stderr: $logDir\parallel_stderr.log"
Write-Host ""
Write-Host "Monitor: Get-Content $logDir\parallel.log -Wait"
