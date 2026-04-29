param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8011,
    [string]$LogLevel = "info",
    [int]$PortScanLimit = 20,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LocalConfig = Join-Path $RepoRoot "ashare_similarity.local.ps1"
if (Test-Path $LocalConfig) {
    . $LocalConfig
}

$RunLogDir = Join-Path $RepoRoot "run_logs"
if (-not (Test-Path $RunLogDir)) {
    New-Item -ItemType Directory -Path $RunLogDir | Out-Null
}

$StatePath = Join-Path $RunLogDir "web_server.json"
$StdoutPath = Join-Path $RunLogDir "web_stdout.log"
$StderrPath = Join-Path $RunLogDir "web_stderr.log"

try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    $PythonExe = $pythonCmd.Source
}
catch {
    throw "Python was not found on PATH. Please install Python or add it to PATH first."
}

$existingPyPath = $env:PYTHONPATH
$env:PYTHONPATH = (Join-Path $RepoRoot "src")
if ($existingPyPath) {
    $env:PYTHONPATH = $env:PYTHONPATH + ";" + $existingPyPath
}

if (Test-Path $StatePath) {
    try {
        $existing = Get-Content $StatePath -Raw | ConvertFrom-Json
        if ($existing.pid) {
            $proc = Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }
        }
    }
    catch {
    }
}

$env:ASHARE_WEB_HOST = $BindHost
$env:ASHARE_WEB_PORT = [string]$Port
$env:ASHARE_WEB_SCAN = [string]$PortScanLimit
$launchCode = @'
import json
import os

from ashare_similarity.web_launcher import build_launch_info

launch = build_launch_info(
    os.environ["ASHARE_WEB_HOST"],
    int(os.environ["ASHARE_WEB_PORT"]),
    scan_limit=int(os.environ["ASHARE_WEB_SCAN"]),
)
print(json.dumps(launch.as_dict(), ensure_ascii=False))
'@
$launch = ($launchCode | & $PythonExe -) | ConvertFrom-Json

if (Test-Path $StdoutPath) { Remove-Item $StdoutPath -Force }
if (Test-Path $StderrPath) { Remove-Item $StderrPath -Force }

$serveArgs = @(
    "-m", "ashare_similarity.cli",
    "serve",
    "--host", $BindHost,
    "--port", [string]$launch.port,
    "--log-level", $LogLevel,
    "--port-scan-limit", "0"
)

$proc = Start-Process -FilePath $PythonExe -ArgumentList $serveArgs -WorkingDirectory $RepoRoot -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath -WindowStyle Hidden -PassThru

$ready = $false
$readyUrl = $null
$healthUrls = @()
if ($launch.browser_url) {
    $healthUrls += ($launch.browser_url.TrimEnd("/") + "/api/healthz")
}
foreach ($url in $launch.access_urls) {
    $candidate = ($url.TrimEnd("/") + "/api/healthz")
    if ($healthUrls -notcontains $candidate) {
        $healthUrls += $candidate
    }
}

for ($attempt = 0; $attempt -lt 60; $attempt++) {
    foreach ($healthUrl in $healthUrls) {
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                $readyUrl = $healthUrl.Substring(0, $healthUrl.Length - "/api/healthz".Length)
                break
            }
        }
        catch {
        }
    }
    if ($ready) {
        break
    }
    Start-Sleep -Milliseconds 500
}

if (-not $ready) {
    Write-Host "Web server failed to start. Check the logs below." -ForegroundColor Red
    Write-Host "  stdout: $StdoutPath"
    Write-Host "  stderr: $StderrPath"
    if (Test-Path $StderrPath) {
        Write-Host ""
        Get-Content $StderrPath -Tail 50
    }
    exit 1
}

$state = [ordered]@{
    pid = $proc.Id
    host = $BindHost
    port = [int]$launch.port
    browser_url = [string]$launch.browser_url
    access_urls = @($launch.access_urls)
    ready_url = $readyUrl
    data_home = $env:ASHARE_SIMILARITY_HOME
    stdout_log = $StdoutPath
    stderr_log = $StderrPath
    started_at = (Get-Date).ToString("s")
}
$state | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $StatePath

Write-Host ""
Write-Host "A-share similarity web is running." -ForegroundColor Green
Write-Host "Preferred URL: $($launch.browser_url)"
Write-Host "Available URLs:"
foreach ($url in $launch.access_urls) {
    Write-Host "  $url"
}
Write-Host "Log directory: $RunLogDir"

if (-not $NoBrowser) {
    Start-Process $launch.browser_url
}
