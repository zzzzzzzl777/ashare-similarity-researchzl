$ErrorActionPreference = "Stop"

param(
    [string]$RuntimeRoot = $env:ASHARE_SIMILARITY_RUNTIME_DATA,
    [switch]$SkipDailyBars
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ArtifactsDir = Join-Path $RepoRoot "artifacts"

if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    $RuntimeRoot = "E:\ashare_similarity_runtime\data"
}

$CoreArchive = Join-Path $ArtifactsDir "live1457_phasec_core_20260521.tar.gz"
$DailyArchive = Join-Path $ArtifactsDir "live1457_daily_bars_20260514.tar.gz"

if (-not (Test-Path $CoreArchive)) {
    throw "Missing $CoreArchive. Run git lfs pull after cloning the repository."
}
if (-not $SkipDailyBars -and -not (Test-Path $DailyArchive)) {
    throw "Missing $DailyArchive. Run git lfs pull, or rerun with -SkipDailyBars."
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

Write-Output "Extracting core 14:57 runtime artifacts to $RuntimeRoot ..."
tar -xzf $CoreArchive -C $RuntimeRoot

if (-not $SkipDailyBars) {
    Write-Output "Extracting daily bars snapshot to $RuntimeRoot ..."
    tar -xzf $DailyArchive -C $RuntimeRoot
}

$Desktop = [Environment]::GetFolderPath("Desktop")
New-Item -ItemType Directory -Force -Path (Join-Path $Desktop "realtime_1457_outputs") | Out-Null

Write-Output ""
Write-Output "Bootstrap complete."
Write-Output "Set for this shell if you used a custom runtime path:"
Write-Output "  `$env:ASHARE_SIMILARITY_RUNTIME_DATA = `"$RuntimeRoot`""
Write-Output ""
Write-Output "Start the web console:"
Write-Output "  powershell -ExecutionPolicy Bypass -File scripts\start_1457_web.ps1"
