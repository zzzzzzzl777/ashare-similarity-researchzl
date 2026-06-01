# Launch cyq_perf gap repair in background
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs\data_backfill_2020_2026"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$proc = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $scriptDir "repair_cyq_perf_gaps.py") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput (Join-Path $logDir "cyq_perf_repair_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "cyq_perf_repair_stderr.log") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "cyq_perf gap repair started!"
Write-Host "  PID: $($proc.Id)"
Write-Host "  Status: $logDir\status_cyq_perf_repair.json"
Write-Host "  Main log: $logDir\cyq_perf_repair.log"
Write-Host "  API log: $logDir\cyq_perf_repair_api.log"
Write-Host ""
Write-Host "Monitor: Get-Content $logDir\cyq_perf_repair.log -Wait"
