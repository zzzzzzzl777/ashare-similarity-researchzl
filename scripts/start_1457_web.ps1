$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "C:\Python314\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$Port = 8765
$LogDir = Join-Path $RepoRoot "run_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$OutLog = Join-Path $LogDir "1457_web_service.out.log"
$ErrLog = Join-Path $LogDir "1457_web_service.err.log"

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    try {
        Stop-Process -Id $listener.OwningProcess -Force -ErrorAction Stop
    } catch {
        Write-Warning "Could not stop process $($listener.OwningProcess): $_"
    }
}

Start-Process -FilePath $Python `
    -ArgumentList @("scripts\serve_1457_picker_web.py", "--host", "0.0.0.0", "--port", "$Port") `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden

Start-Sleep -Seconds 3
$code = curl.exe -s -o NUL -w "%{http_code}" "http://127.0.0.1:$Port/api/status"
if ($code -ne "200") {
    throw "1457 web failed health check on port $Port; HTTP $code"
}

Write-Output "1457 web is running on http://127.0.0.1:$Port/ and http://100.65.186.118:$Port/"
