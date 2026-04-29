param(
    [int]$BatchSize = 64,
    [int]$PollSeconds = 30,
    [int]$StopAfterNoProgress = 60
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$LocalConfig = Join-Path $workspace "ashare_similarity.local.ps1"
if (Test-Path $LocalConfig) {
    . $LocalConfig
}

function Invoke-PythonStep {
    param(
        [string]$Title,
        [string[]]$ArgumentList
    )

    Write-Host ("[prepare-daily] {0}" -f $Title) -ForegroundColor Cyan
    & python @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw ("Step failed: {0}" -f $Title)
    }
}

function Get-DailyStatus {
    $raw = & python -m ashare_similarity.cli status --frequency daily
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read daily status."
    }
    if (-not $raw) {
        throw "Did not receive any status output."
    }
    return $raw | ConvertFrom-Json
}

function Invoke-DailyBackfill {
    Invoke-PythonStep -Title ("Start daily backfill, batch_size={0}" -f $BatchSize) -ArgumentList @(
        "-m", "ashare_similarity.cli",
        "backfill",
        "--frequency", "daily",
        "--batch-size", "$BatchSize",
        "--retry-failures"
    )
}

function Invoke-DailyIndexRebuild {
    $windows = 5, 8, 10, 20
    foreach ($window in $windows) {
        Invoke-PythonStep -Title ("Rebuild daily window {0} index" -f $window) -ArgumentList @(
            "-m", "ashare_similarity.cli",
            "build",
            "--frequency", "daily",
            "--window-size", "$window",
            "--skip-refresh"
        )
    }
}

function Invoke-DailyDoctor {
    param(
        [string]$EndDate
    )

    $raw = & python -m ashare_similarity.cli doctor --frequency daily --window-size 10 --symbol 000333 --end-date $EndDate
    if ($LASTEXITCODE -ne 0) {
        throw "Daily doctor check failed."
    }
    if (-not $raw) {
        throw "Daily doctor check did not return any output."
    }
    return $raw | ConvertFrom-Json
}

function Assert-DailyReadyStatus {
    param(
        [pscustomobject]$Status
    )

    $cache = $Status.cache_status.daily
    $health = $Status.index_health.daily
    $cached = [int]$cache.cached_symbols
    $filtered = [int]$Status.filtered_universe_count
    $missing = @($health.missing_windows)
    $stale = @($health.stale_windows)
    $indexSymbols = [int]$health.current_index_symbol_count
    $windowCounts = $health.window_symbol_counts

    if ($cached -lt $filtered) {
        throw ("Daily cache is incomplete: {0}/{1}" -f $cached, $filtered)
    }
    if ($missing.Count -gt 0) {
        throw ("Daily indexes are missing windows: {0}" -f (($missing | ForEach-Object { [string]$_ }) -join ", "))
    }
    if ($stale.Count -gt 0) {
        throw ("Daily indexes are stale: {0}" -f (($stale | ForEach-Object { [string]$_ }) -join ", "))
    }
    if ($indexSymbols -le 0 -or $indexSymbols -gt $cached) {
        throw ("Daily index coverage is invalid: index={0}, cache={1}" -f $indexSymbols, $cached)
    }
    foreach ($window in @(5, 8, 10, 20)) {
        $key = [string]$window
        $count = 0
        if ($null -ne $windowCounts -and $null -ne $windowCounts.$key) {
            $count = [int]$windowCounts.$key
        }
        if ($count -le 0 -or $count -gt $cached) {
            throw ("Daily window {0} coverage is invalid: index={1}, cache={2}" -f $window, $count, $cached)
        }

        $entryName = "daily_{0}" -f $window
        $entry = $Status.index_status.$entryName
        if ($null -eq $entry) {
            throw ("Daily window {0} is missing from index status." -f $window)
        }
        if ([bool]$entry.stale) {
            throw ("Daily window {0} is stale." -f $window)
        }
        if ([bool]$entry.artifact_missing) {
            throw ("Daily window {0} is missing index artifacts." -f $window)
        }

        $builtSymbols = 0
        if ($null -ne $entry.metadata -and $null -ne $entry.metadata.built_from -and $null -ne $entry.metadata.built_from.symbols_count) {
            $builtSymbols = [int]$entry.metadata.built_from.symbols_count
        }
        if ($builtSymbols -gt 0 -and $builtSymbols -lt $cached) {
            throw ("Daily window {0} was built from an incomplete cache: built_from={1}, cache={2}" -f $window, $builtSymbols, $cached)
        }
    }
    if (-not [bool]$health.search_ready) {
        throw "Daily index health is not search ready."
    }
    if (-not [bool]$health.research_ready) {
        throw "Daily index health is not research ready."
    }
}

function Write-ReadyArtifact {
    param(
        [pscustomobject]$Status,
        [pscustomobject]$Doctor
    )

    $artifactPath = Join-Path $workspace "run_logs\daily_ready.json"
    $artifact = [ordered]@{
        generated_at = (Get-Date).ToString("s")
        status = $Status
        doctor = $Doctor
    }
    $artifact | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $artifactPath
    Write-Host ("[prepare-daily] Ready artifact written: {0}" -f $artifactPath) -ForegroundColor Green
}

$lastCached = -1
$noProgressPolls = 0

while ($true) {
    $status = Get-DailyStatus
    $cache = $status.cache_status.daily
    $latest = $status.latest_backfill
    $cached = [int]$cache.cached_symbols
    $filtered = [int]$status.filtered_universe_count
    $remaining = $filtered - $cached

    Write-Host ("[prepare-daily] Cache {0}/{1}, remaining {2}" -f $cached, $filtered, $remaining) -ForegroundColor Green

    if ($cached -gt $lastCached) {
        $lastCached = $cached
        $noProgressPolls = 0
    }
    else {
        $noProgressPolls += 1
    }

    if ($cached -ge $filtered) {
        break
    }

    if ($noProgressPolls -ge $StopAfterNoProgress) {
        throw ("No cache progress for {0} polls. Last cached={1}/{2}" -f $noProgressPolls, $cached, $filtered)
    }

    if ($null -ne $latest -and $latest.status -eq "running") {
        Write-Host ("[prepare-daily] Existing backfill is still running, waiting for next poll ... (no-progress polls: {0}/{1})" -f $noProgressPolls, $StopAfterNoProgress) -ForegroundColor DarkYellow
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    Invoke-DailyBackfill
    Start-Sleep -Seconds $PollSeconds
}

Write-Host "[prepare-daily] Daily cache is full. Check default daily indexes." -ForegroundColor Green
$readyStatus = Get-DailyStatus
$readyHealth = $readyStatus.index_health.daily
$readyMissing = @($readyHealth.missing_windows)
$readyStale = @($readyHealth.stale_windows)
if ($readyMissing.Count -eq 0 -and $readyStale.Count -eq 0 -and [bool]$readyHealth.search_ready -and [bool]$readyHealth.research_ready) {
    Write-Host "[prepare-daily] Default daily indexes are already ready. Skip rebuild." -ForegroundColor Green
}
else {
    Write-Host "[prepare-daily] Start rebuilding default daily indexes." -ForegroundColor Green
    Invoke-DailyIndexRebuild
}

$finalStatus = Get-DailyStatus
$finalCache = [int]$finalStatus.cache_status.daily.cached_symbols
$finalFiltered = [int]$finalStatus.filtered_universe_count
$finalRemaining = $finalFiltered - $finalCache
Write-Host ("[prepare-daily] Final cache {0}/{1}, remaining {2}" -f $finalCache, $finalFiltered, $finalRemaining) -ForegroundColor Green
Assert-DailyReadyStatus -Status $finalStatus

$doctorDate = $finalStatus.cache_status.daily.data_freshness.latest_data_at
if ($doctorDate) {
    $doctorDate = ([datetime]$doctorDate).ToString("yyyy-MM-dd")
} else {
    $doctorDate = (Get-Date).ToString("yyyy-MM-dd")
}

Write-Host "[prepare-daily] Run final doctor check ..." -ForegroundColor Green
$doctor = Invoke-DailyDoctor -EndDate $doctorDate
if (-not [bool]$doctor.overall_ready) {
    throw "Daily doctor check did not pass overall_ready=true."
}
Write-ReadyArtifact -Status $finalStatus -Doctor $doctor
