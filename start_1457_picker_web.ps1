param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$RunLogDir = Join-Path $RepoRoot "run_logs"
if (-not (Test-Path $RunLogDir)) {
    New-Item -ItemType Directory -Path $RunLogDir | Out-Null
}

$StatePath = Join-Path $RunLogDir "1457_picker_web_state.json"
$StdoutPath = Join-Path $RunLogDir "1457_picker_web_stdout.log"
$StderrPath = Join-Path $RunLogDir "1457_picker_web_stderr.log"

try {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}
catch {
    throw "Python was not found on PATH."
}

if (Test-Path $StatePath) {
    try {
        $existing = Get-Content $StatePath -Raw | ConvertFrom-Json
        if ($existing.pid) {
            Stop-Process -Id ([int]$existing.pid) -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
    catch {
    }
}

if (Test-Path $StdoutPath) { Remove-Item $StdoutPath -Force }
if (Test-Path $StderrPath) { Remove-Item $StderrPath -Force }

$ServeArgs = @(
    "scripts\serve_1457_picker_web.py",
    "--host", $BindHost,
    "--port", [string]$Port
)

$proc = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $ServeArgs `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -WindowStyle Hidden `
    -PassThru

$Url = "http://$BindHost`:$Port/"
$ready = $false
for ($attempt = 0; $attempt -lt 50; $attempt++) {
    try {
        $resp = Invoke-WebRequest -Uri ($Url.TrimEnd("/") + "/api/status") -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch {
    }
    Start-Sleep -Milliseconds 500
}

$state = [ordered]@{
    pid = $proc.Id
    url = $Url
    stdout = $StdoutPath
    stderr = $StderrPath
    started_at = (Get-Date).ToString("s")
}
$state | ConvertTo-Json | Set-Content -Path $StatePath -Encoding UTF8

if (-not $ready) {
    Write-Host "14:57 picker web failed to start." -ForegroundColor Red
    Write-Host "stdout: $StdoutPath"
    Write-Host "stderr: $StderrPath"
    if (Test-Path $StderrPath) {
        Get-Content $StderrPath -Tail 50
    }
    exit 1
}

Write-Host "14:57 picker web is running." -ForegroundColor Green
Write-Host "URL: $Url"
Write-Host "PID: $($proc.Id)"
Write-Host "Logs: $RunLogDir"

if (-not $NoBrowser) {
    Start-Process $Url
}
