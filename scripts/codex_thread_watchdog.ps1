param(
    [Parameter(Mandatory=$true)][string]$ThreadId,
    [Parameter(Mandatory=$true)][string]$JsonlPath,
    [int]$MaxTokens = 80000,
    [int]$IntervalSeconds = 8,
    [int]$WarnJsonlMB = 20,
    [int]$DangerJsonlMB = 60,
    [int]$StopAfterMinutes = 0,
    [string]$LogPath = ""
)

$ErrorActionPreference = "Continue"

$codexHome = Join-Path $env:USERPROFILE ".codex"
$stateDb = Join-Path $codexHome "state_5.sqlite"

if (-not $LogPath) {
    $safeId = $ThreadId -replace '[^A-Za-z0-9_-]', '_'
    $logDir = Join-Path (Get-Location) "run_logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $LogPath = Join-Path $logDir ("codex_thread_watchdog_{0}_{1}.log" -f $safeId, (Get-Date -Format "yyyyMMdd-HHmmss"))
}

function Write-WatchLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

Write-WatchLog "start thread=$ThreadId max_tokens=$MaxTokens interval=${IntervalSeconds}s jsonl=$JsonlPath"

$started = Get-Date
while ($true) {
    try {
        $py = @'
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--thread-id", required=True)
parser.add_argument("--max-tokens", type=int, required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db, timeout=10)
cur = conn.cursor()
row = cur.execute(
    "select id, title, tokens_used, updated_at from threads where id=?",
    (args.thread_id,),
).fetchone()
if not row:
    print("missing")
else:
    tid, title, tokens, updated_at = row
    changed = 0
    if tokens > args.max_tokens:
        cur.execute(
            "update threads set tokens_used=? where id=? and tokens_used>?",
            (args.max_tokens, args.thread_id, args.max_tokens),
        )
        conn.commit()
        changed = cur.rowcount
        tokens = args.max_tokens
    print(f"thread={tid} title={title} tokens={tokens} updated_at={updated_at} reset={changed}")
conn.close()
'@
        $result = $py | python - --db $stateDb --thread-id $ThreadId --max-tokens $MaxTokens
        Write-WatchLog $result
    } catch {
        Write-WatchLog ("state_error " + $_.Exception.Message)
    }

    try {
        if (Test-Path -LiteralPath $JsonlPath) {
            $item = Get-Item -LiteralPath $JsonlPath
            $mb = [math]::Round($item.Length / 1MB, 2)
            $level = "ok"
            if ($mb -ge $DangerJsonlMB) { $level = "danger" }
            elseif ($mb -ge $WarnJsonlMB) { $level = "warn" }
            Write-WatchLog ("jsonl_mb={0} level={1} mtime={2:o}" -f $mb, $level, $item.LastWriteTime)
        } else {
            Write-WatchLog "jsonl_missing"
        }
    } catch {
        Write-WatchLog ("jsonl_error " + $_.Exception.Message)
    }

    if ($StopAfterMinutes -gt 0) {
        $elapsed = ((Get-Date) - $started).TotalMinutes
        if ($elapsed -ge $StopAfterMinutes) {
            Write-WatchLog "stop elapsed_minutes=$([math]::Round($elapsed, 2))"
            break
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
