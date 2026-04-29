param(
    [int]$BatchSize = 20,
    [int]$MaxSymbolsPerRound = 400,
    [int]$MaxRounds = 20,
    [int]$RetryFailuresEvery = 3,
    [int]$StopAfterIdleRounds = 3
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LocalConfig = Join-Path $RepoRoot "ashare_similarity.local.ps1"
if (Test-Path $LocalConfig) {
    . $LocalConfig
}

function Invoke-Step {
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

Invoke-Step -Title "Status before cache expansion" -ArgumentList @(
    "-m", "ashare_similarity.cli",
    "status",
    "--frequency", "daily"
)

Invoke-Step -Title "Expand free daily cache with missing-first backfill" -ArgumentList @(
    "-m", "ashare_similarity.cli",
    "backfill-loop",
    "--frequency", "daily",
    "--batch-size", "$BatchSize",
    "--max-symbols-per-round", "$MaxSymbolsPerRound",
    "--max-rounds", "$MaxRounds",
    "--round-interval-seconds", "0",
    "--retry-failures-every", "$RetryFailuresEvery",
    "--stop-after-idle-rounds", "$StopAfterIdleRounds"
)

Invoke-Step -Title "Status after cache expansion" -ArgumentList @(
    "-m", "ashare_similarity.cli",
    "status",
    "--frequency", "daily"
)

Write-Host ""
Write-Host "Tip: run prepare_daily_ready.bat after cache growth. Delivery is not ready until daily_ready.json is generated." -ForegroundColor Yellow
