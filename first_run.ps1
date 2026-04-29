param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8011,
    [switch]$NoBrowser,
    [switch]$QuickDemo,
    [int]$NoProgressPollLimit = 60
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LocalConfig = Join-Path $RepoRoot "ashare_similarity.local.ps1"
if (Test-Path $LocalConfig) {
    . $LocalConfig
}

function Invoke-PythonStep {
    param(
        [string]$Title,
        [string[]]$ArgumentList
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    & python @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Title"
    }
}

function Invoke-PowerShellStep {
    param(
        [string]$Title,
        [string]$ScriptPath,
        [string[]]$ArgumentList = @()
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Title"
    }
}

if ($QuickDemo) {
    Write-Host "QuickDemo is for smoke testing only; it is not a full delivery gate." -ForegroundColor Yellow
    Invoke-PowerShellStep -Title "Stop existing web server before maintenance" -ScriptPath (
        Join-Path $RepoRoot "stop_web.ps1"
    )
    Invoke-PythonStep -Title "Bootstrap universe and load a small demo sample" -ArgumentList @(
        "-m", "ashare_similarity.cli", "bootstrap", "--with-sample"
    )
    Invoke-PythonStep -Title "Backfill one demo batch and rebuild demo-ready daily indexes" -ArgumentList @(
        "-m", "ashare_similarity.cli",
        "maintain",
        "--frequency", "daily",
        "--batch-size", "10",
        "--max-symbols-per-round", "50",
        "--max-rounds", "1",
        "--round-interval-seconds", "0",
        "--retry-failures-every", "1"
    )
    Invoke-PythonStep -Title "Run doctor check" -ArgumentList @("-m", "ashare_similarity.cli", "doctor")
}
else {
    Invoke-PowerShellStep -Title "Stop existing web server before maintenance" -ScriptPath (
        Join-Path $RepoRoot "stop_web.ps1"
    )
    Invoke-PythonStep -Title "Bootstrap universe and base market context" -ArgumentList @(
        "-m", "ashare_similarity.cli", "bootstrap"
    )
    Invoke-PowerShellStep -Title "Prepare full free daily cache and default indexes" -ScriptPath (
        Join-Path $RepoRoot "prepare_daily_ready.ps1"
    ) -ArgumentList @("-BatchSize", "64", "-PollSeconds", "30", "-StopAfterNoProgress", "$NoProgressPollLimit")
}

Write-Host ""
Write-Host "==> Start Web" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "start_web.ps1") -BindHost $BindHost -Port $Port -NoBrowser:$NoBrowser
