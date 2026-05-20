# Launch stk_mins_5 gap repair in background
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $projectRoot "logs\data_backfill_2020_2026"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$proc = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $scriptDir "repair_stk_mins_gaps.py") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput (Join-Path $logDir "repair_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "repair_stderr.log") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "stk_mins_5 gap repair started!"
Write-Host "  PID: $($proc.Id)"
Write-Host "  Status: $logDir\status_stk_mins_repair.json"
Write-Host "  Main log: $logDir\stk_mins_repair.log"
Write-Host "  API log: $logDir\stk_mins_repair_api.log"
Write-Host "  Stderr: $logDir\repair_stderr.log"
Write-Host ""
Write-Host "Monitor: Get-Content $logDir\stk_mins_repair.log -Wait"
