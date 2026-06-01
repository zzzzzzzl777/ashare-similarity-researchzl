$ErrorActionPreference = "Continue"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$StartScript = Join-Path $RepoRoot "scripts\start_1457_web.ps1"
$Port = 8765
$LogDir = Join-Path $RepoRoot "run_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$WatchLog = Join-Path $LogDir "1457_web_watchdog.log"

function Write-WatchLog($Message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $WatchLog -Value "[$ts] $Message" -Encoding UTF8
}

Write-WatchLog "watchdog started"

while ($true) {
    try {
        $code = curl.exe -s -o NUL -w "%{http_code}" "http://127.0.0.1:$Port/api/status"
        if ($code -ne "200") {
            Write-WatchLog "health check failed: HTTP $code; restarting"
            powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript | Out-Null
        }
    } catch {
        Write-WatchLog "health check error: $_; restarting"
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript | Out-Null
    }
    Start-Sleep -Seconds 30
}
