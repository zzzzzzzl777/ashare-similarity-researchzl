# Start data backfill pipeline in background
# Logs: logs\data_backfill_2020_2026\
# Status: logs\data_backfill_2020_2026\status.json

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs\data_backfill_2020_2026"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$proc = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $scriptDir "run_data_backfill.py") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput (Join-Path $logDir "stdout.log") `
    -RedirectStandardError (Join-Path $logDir "stderr.log") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Backfill pipeline started!"
Write-Host "  PID: $($proc.Id)"
Write-Host "  Status: $logDir\status.json"
Write-Host "  Main log: $logDir\main.log"
Write-Host "  Paid API log: $logDir\paid_api.log"
Write-Host "  Stdout: $logDir\stdout.log"
Write-Host "  Stderr: $logDir\stderr.log"
Write-Host ""
Write-Host "Monitor: Get-Content $logDir\main.log -Wait"
