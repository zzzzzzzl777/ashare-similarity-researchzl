param(
    [int[]]$WindowSizes = @(5, 8, 10, 20)
)

$ErrorActionPreference = "Stop"

$TrailingWindowSizes = @()
foreach ($Arg in $args) {
    if ($Arg -notmatch '^\d+$') {
        throw "Unexpected argument: $Arg"
    }
    $TrailingWindowSizes += [int]$Arg
}

if ($TrailingWindowSizes.Count -gt 0) {
    $WindowSizes = @($WindowSizes) + $TrailingWindowSizes
}
$WindowSizes = @($WindowSizes | Select-Object -Unique)

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

foreach ($WindowSize in $WindowSizes) {
    Invoke-Step -Title "Build daily window $WindowSize" -ArgumentList @(
        "-m", "ashare_similarity.cli",
        "build",
        "--frequency", "daily",
        "--window-size", "$WindowSize",
        "--skip-refresh"
    )
}

Invoke-Step -Title "Status after index rebuild" -ArgumentList @(
    "-m", "ashare_similarity.cli",
    "status",
    "--frequency", "daily"
)
