$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$WatchScript = Join-Path $RepoRoot "scripts\watch_1457_web.ps1"
$TaskName = "Ashare1457WebWatchdog"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchScript`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Keep the 14:57 realtime candidate web UI online and auto-warm on access." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Output "Installed and started scheduled task: $TaskName"
