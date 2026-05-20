# Launch per-date API gap repair in background
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs\data_backfill_2020_2026"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$proc = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $scriptDir "repair_perdate_gaps.py") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput (Join-Path $logDir "perdate_repair_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "perdate_repair_stderr.log") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Per-date API gap repair started!"
Write-Host "  PID: $($proc.Id)"
Write-Host "  Status: $logDir\status_perdate_repair.json"
Write-Host "  Main log: $logDir\perdate_repair.log"
Write-Host "  API log: $logDir\perdate_repair_api.log"
Write-Host ""
Write-Host "Monitor: Get-Content $logDir\perdate_repair.log -Wait"
