# start_new_data_pull.ps1 — Launch all 3 data pull scripts as background processes
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_new_data_pull.ps1

$scriptDir = "c:\Users\zzzzzzl\Desktop\subagent\scripts"
$python = "python"
$logDir = "c:\Users\zzzzzzl\Desktop\subagent\logs\data_backfill_2020_2026"

Write-Host "Starting data pull processes..." -ForegroundColor Cyan

# Stream 1: Per-date APIs (12 APIs, ~1.8 hours)
$p1 = Start-Process -FilePath $python -ArgumentList "$scriptDir\pull_new_perdate_apis.py" -WindowStyle Hidden -PassThru
Write-Host "  [1] pull_new_perdate_apis.py  PID=$($p1.Id)" -ForegroundColor Green

# Stream 2: 1-minute K-line (3196 stocks, ~3 days)
$p2 = Start-Process -FilePath $python -ArgumentList "$scriptDir\pull_stk_mins_1min.py" -WindowStyle Hidden -PassThru
Write-Host "  [2] pull_stk_mins_1min.py     PID=$($p2.Id)" -ForegroundColor Green

# Stream 3: Per-stock pledge_stat (~36 minutes)
$p3 = Start-Process -FilePath $python -ArgumentList "$scriptDir\pull_pledge_stat_perstock.py" -WindowStyle Hidden -PassThru
Write-Host "  [3] pull_pledge_stat_perstock.py PID=$($p3.Id)" -ForegroundColor Green

Write-Host ""
Write-Host "All 3 processes launched. Monitor status via:" -ForegroundColor Yellow
Write-Host "  type $logDir\status_new_perdate.json"
Write-Host "  type $logDir\status_stk_mins_1min.json"
Write-Host "  type $logDir\status_pledge_stat.json"
Write-Host ""
Write-Host "Logs:"
Write-Host "  $logDir\new_perdate.log"
Write-Host "  $logDir\stk_mins_1min.log"
Write-Host "  $logDir\pledge_stat.log"
