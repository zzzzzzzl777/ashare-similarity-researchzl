param()

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StatePath = Join-Path (Join-Path $RepoRoot "run_logs") "web_server.json"

if (-not (Test-Path $StatePath)) {
    Write-Host "No running web state file was found."
    exit 0
}

try {
    $state = Get-Content $StatePath -Raw | ConvertFrom-Json
}
catch {
    Write-Host "State file could not be parsed. Skipping."
    exit 0
}

if ($state.pid) {
    $proc = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped web process PID $($proc.Id)."
    }
    else {
        Write-Host "The PID stored in the state file no longer exists."
    }
}

Remove-Item $StatePath -Force -ErrorAction SilentlyContinue
