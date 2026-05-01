param(
    [int]$MaxJsonlMB = 15,
    [int]$MaxTokens = 80000,
    [switch]$ResetTokenCounts
)

$ErrorActionPreference = "Stop"

$codexHome = Join-Path $env:USERPROFILE ".codex"
$sessionsRoot = Join-Path $codexHome "sessions"
$stateDb = Join-Path $codexHome "state_5.sqlite"
$backupRoot = Join-Path (Get-Location) ("codex_context_guard_backup_" + (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "Codex context guard"
Write-Host "Codex home: $codexHome"
Write-Host "Max JSONL MB: $MaxJsonlMB"
Write-Host "Max tokens: $MaxTokens"
Write-Host ""

if (Test-Path -LiteralPath $sessionsRoot) {
    $limitBytes = [int64]$MaxJsonlMB * 1MB
    $large = Get-ChildItem -LiteralPath $sessionsRoot -Recurse -File -Filter "*.jsonl" |
        Where-Object { $_.Length -gt $limitBytes } |
        Sort-Object Length -Descending |
        Select-Object -First 30 FullName, Length, LastWriteTime

    if ($large) {
        Write-Host "Large live JSONL sessions:"
        $large | Format-Table -AutoSize
    } else {
        Write-Host "No live JSONL sessions above ${MaxJsonlMB}MB."
    }
} else {
    Write-Host "Sessions root not found: $sessionsRoot"
}

Write-Host ""

if (-not (Test-Path -LiteralPath $stateDb)) {
    Write-Host "State DB not found: $stateDb"
    exit 0
}

$py = @'
import argparse
import shutil
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--max-tokens", type=int, required=True)
parser.add_argument("--reset", action="store_true")
parser.add_argument("--backup-dir", required=True)
args = parser.parse_args()

db = Path(args.db)
conn = sqlite3.connect(str(db), timeout=10)
cur = conn.cursor()

rows = list(cur.execute(
    "select id, title, tokens_used, updated_at from threads "
    "where tokens_used > ? order by tokens_used desc",
    (args.max_tokens,),
))

if rows:
    print("Threads above token threshold:")
    for tid, title, tokens, updated_at in rows[:50]:
        print(f"{tokens:>12}  {tid}  {title}  updated_at={updated_at}")
else:
    print("No threads above token threshold.")

if args.reset and rows:
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "state_5.sqlite.before-token-reset.bak"
    conn.close()
    shutil.copy2(db, backup)
    conn = sqlite3.connect(str(db), timeout=10)
    cur = conn.cursor()
    cur.execute(
        "update threads set tokens_used = ? where tokens_used > ?",
        (args.max_tokens, args.max_tokens),
    )
    conn.commit()
    print(f"Reset {cur.rowcount} thread token counters to {args.max_tokens}.")
    print(f"State DB backup: {backup}")

conn.close()
'@

$pythonArgs = @("--db", $stateDb, "--max-tokens", "$MaxTokens", "--backup-dir", $backupRoot)
if ($ResetTokenCounts) { $pythonArgs += "--reset" }
$py | python - @pythonArgs

Write-Host ""
Write-Host "Tip: if a restored thread starts auto-compacting again, use:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\codex_context_guard.ps1 -ResetTokenCounts"
