#!/usr/bin/env python3
"""Local supervisor for a running Codex Desktop thread.

This watches the real token_count events in a target rollout JSONL. When the
live input context gets too large, it backs up the thread files and replaces the
rollout with a compact continuation that points at durable project state files.
It does not stop or modify project/training processes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def local_human() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except Exception as exc:  # pragma: no cover - diagnostic path
                    errors.append(f"line={line_no} {type(exc).__name__}: {exc}")
    except FileNotFoundError:
        errors.append("jsonl_missing")
    return records, errors


def append_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{local_human()} {message}\n")


def get_latest_token_count(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    for record in reversed(records):
        payload = record.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
        last = info.get("last_token_usage") if isinstance(info.get("last_token_usage"), dict) else {}
        total = info.get("total_token_usage") if isinstance(info.get("total_token_usage"), dict) else {}
        return {
            "timestamp": record.get("timestamp"),
            "input_tokens": int(last.get("input_tokens") or 0),
            "cached_input_tokens": int(last.get("cached_input_tokens") or 0),
            "output_tokens": int(last.get("output_tokens") or 0),
            "reasoning_output_tokens": int(last.get("reasoning_output_tokens") or 0),
            "total_tokens": int(last.get("total_tokens") or 0),
            "model_context_window": int(info.get("model_context_window") or 0),
            "total_input_tokens": int(total.get("input_tokens") or 0),
        }
    return None


def get_latest_agent_message(records: list[dict[str, Any]]) -> str:
    for record in reversed(records):
        payload = record.get("payload")
        if isinstance(payload, dict) and payload.get("type") == "agent_message":
            message = payload.get("message")
            if isinstance(message, str):
                return message[:2000]
        if isinstance(payload, dict) and payload.get("type") == "message" and payload.get("role") == "assistant":
            parts = payload.get("content")
            if isinstance(parts, list):
                texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "output_text"]
                text = "\n".join(t for t in texts if t)
                if text:
                    return text[:2000]
    return ""


def pending_tool_calls(records: list[dict[str, Any]]) -> set[str]:
    calls: set[str] = set()
    done: set[str] = set()
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        typ = payload.get("type")
        call_id = payload.get("call_id")
        if isinstance(call_id, str) and typ in {"function_call", "custom_tool_call"}:
            calls.add(call_id)
        if isinstance(call_id, str) and typ in {
            "function_call_output",
            "custom_tool_call_output",
            "exec_command_end",
            "patch_apply_end",
            "collab_waiting_end",
        }:
            done.add(call_id)
    return calls - done


def pending_tool_call_records(records: list[dict[str, Any]], pending: set[str]) -> list[dict[str, Any]]:
    if not pending:
        return []
    kept: list[dict[str, Any]] = []
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("type") not in {"function_call", "custom_tool_call"}:
            continue
        call_id = payload.get("call_id")
        if isinstance(call_id, str) and call_id in pending:
            kept.append(record)
    return kept


def read_live_state(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def write_live_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def active_gpu_processes() -> list[dict[str, str]]:
    ps = (
        "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*gpu-prediction-probe*' -or $_.CommandLine -like '*ashare_similarity.cli backfill*' } | "
        "Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Depth 3"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except Exception as exc:
        return [{"error": f"{type(exc).__name__}: {exc}"}]
    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return [{"raw": raw[:1000]}]
    rows = parsed if isinstance(parsed, list) else [parsed]
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cmd = str(row.get("CommandLine") or "")
        out.append(
            {
                "ProcessId": str(row.get("ProcessId") or ""),
                "CreationDate": str(row.get("CreationDate") or ""),
                "CommandLine": cmd[:800],
            }
        )
    return out


def recent_run_logs(workspace: Path) -> list[dict[str, Any]]:
    run_dir = workspace / "run_logs"
    rows: list[dict[str, Any]] = []
    try:
        files = sorted(run_dir.glob("gpu_probe*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    except Exception:
        return rows
    for path in files:
        item: dict[str, Any] = {
            "file": str(path),
            "size": path.stat().st_size,
            "mtime_local": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if path.stat().st_size > 0:
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    for key in (
                        "status",
                        "accuracy",
                        "confident_accuracy",
                        "confident_coverage",
                        "confident_count",
                        "acceptance_passed",
                        "feature_set",
                        "max_selected_features",
                        "feature_selection_method",
                        "candidate_family",
                    ):
                        if key in data:
                            item[key] = data[key]
                    acceptance = data.get("acceptance")
                    if isinstance(acceptance, dict) and "passed" in acceptance:
                        item["acceptance_passed"] = acceptance["passed"]
            except Exception as exc:
                item["parse_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(item)
    return rows


def reset_db_tokens(db_path: Path, thread_id: str, value: int, max_value: int) -> str:
    try:
        conn = sqlite3.connect(str(db_path), timeout=20)
        cur = conn.cursor()
        row = cur.execute("select tokens_used from threads where id=?", (thread_id,)).fetchone()
        if not row:
            conn.close()
            return "db_thread_missing"
        old = int(row[0] or 0)
        changed = 0
        if old > max_value or value < old:
            cur.execute("update threads set tokens_used=? where id=?", (value, thread_id))
            changed = cur.rowcount
            conn.commit()
        conn.close()
        return f"db_tokens old={old} new={value if changed else old} changed={changed}"
    except Exception as exc:
        return f"db_error {type(exc).__name__}: {exc}"


def first_session_meta(records: list[dict[str, Any]], thread_id: str, workspace: Path) -> dict[str, Any]:
    if records and records[0].get("type") == "session_meta":
        return records[0]
    return {
        "timestamp": utc_iso(),
        "type": "session_meta",
        "payload": {
            "id": thread_id,
            "timestamp": utc_iso(),
            "cwd": str(workspace),
            "originator": "Codex Desktop",
            "source": "local-supervisor",
        },
    }


def build_summary(
    *,
    thread_id: str,
    workspace: Path,
    live_state_path: Path,
    latest: dict[str, Any],
    active: list[dict[str, str]],
    recent_logs: list[dict[str, Any]],
    last_agent_message: str,
    backup_dir: Path,
) -> str:
    active_text = json.dumps(active, ensure_ascii=False, indent=2)
    logs_text = json.dumps(recent_logs[:5], ensure_ascii=False, indent=2)
    latest_text = json.dumps(latest, ensure_ascii=False, indent=2)
    return f"""LOCAL AUTO CONTEXT COMPACTION FOR THREAD {thread_id}

Reason:
- The local supervisor saw real token_count.last_token_usage.input_tokens above the configured danger threshold.
- Remote Codex compact has previously failed for this thread, so the supervisor compacted locally before the context reached the failure zone again.
- Full pre-compact rollout was backed up at: {backup_dir}

Latest token_count before compact:
{latest_text}

Project continuation rule:
- Do not redo broad project checks just because compaction happened.
- Read and follow: {live_state_path}
- Then use only the minimal needed files: docs/handoff_20260501_new_thread.md, docs/prediction_experiment_log.md, current run_logs, and focused tests.
- Never read the full backup JSONL unless the user explicitly asks.
- Keep optimizing the short-term T+1 GPU project toward >=75% high-confidence lockbox accuracy with formal gates.
- Preserve quality; do not lower data size, GPU use, or acceptance standards to save context.

Active project Python processes detected during compact:
{active_text}

Recent run log snapshot:
{logs_text}

Most recent assistant status before compact:
{last_agent_message}
"""


def compact_thread(
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    latest: dict[str, Any],
    log_path: Path,
    pending_records: list[dict[str, Any]] | None = None,
) -> Path:
    workspace = Path(args.workspace)
    jsonl_path = Path(args.jsonl_path)
    db_path = Path(args.state_db)
    session_index = Path(args.session_index)
    live_state_path = Path(args.live_state)

    stamp = local_stamp()
    backup_dir = workspace / f"codex_target_thread_auto_compact_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(jsonl_path, backup_dir / "target_thread_before_auto_compact.jsonl")
    if db_path.exists():
        shutil.copy2(db_path, backup_dir / "state_5_before_auto_compact.sqlite")
    if session_index.exists():
        shutil.copy2(session_index, backup_dir / "session_index_before_auto_compact.jsonl")

    live_state = read_live_state(live_state_path)
    live_state["updated_at_local"] = local_human()
    live_state["supervisor"] = {
        "thread_id": args.thread_id,
        "last_auto_compact_at_local": local_human(),
        "latest_input_tokens_before_compact": latest.get("input_tokens"),
        "latest_model_context_window": latest.get("model_context_window"),
        "backup_dir": str(backup_dir),
        "policy": "Continue from live_run_state.json; do not redo broad checks after compaction.",
    }
    write_live_state(live_state_path, live_state)

    active = active_gpu_processes()
    logs = recent_run_logs(workspace)
    last_agent_message = get_latest_agent_message(records)
    summary = build_summary(
        thread_id=args.thread_id,
        workspace=workspace,
        live_state_path=live_state_path,
        latest=latest,
        active=active,
        recent_logs=logs,
        last_agent_message=last_agent_message,
        backup_dir=backup_dir,
    )
    (backup_dir / "compact_summary.txt").write_text(summary, encoding="utf-8")

    now = utc_iso()
    user_text = (
        "Local supervisor compacted this thread to prevent remote compact failure. "
        f"Continue from {live_state_path}; do not redo broad checks; do not read full backup JSONL."
    )
    compact_records = [
        first_session_meta(records, args.thread_id, workspace),
        {"timestamp": now, "type": "event_msg", "payload": {"type": "context_compacted"}},
        {"timestamp": now, "type": "event_msg", "payload": {"type": "user_message", "message": user_text}},
        {
            "timestamp": now,
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        },
        {"timestamp": now, "type": "event_msg", "payload": {"type": "agent_message", "message": summary, "phase": "commentary", "memory_citation": None}},
        {
            "timestamp": now,
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": summary}],
                "phase": "commentary",
            },
        },
    ]
    pending_records = pending_records or []
    compact_records.extend(pending_records)
    if not pending_records:
        compact_records.append(
            {
                "timestamp": now,
                "type": "event_msg",
                "payload": {"type": "task_complete", "turn_id": f"local-auto-compact-{stamp}", "last_agent_message": summary},
            }
        )

    compact_text = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in compact_records
    )
    tmp = jsonl_path.with_suffix(jsonl_path.suffix + ".supervisor.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(compact_text)
    replaced = False
    last_replace_error: Exception | None = None
    for _ in range(5):
        try:
            os.replace(tmp, jsonl_path)
            replaced = True
            break
        except PermissionError as exc:
            last_replace_error = exc
            time.sleep(0.25)
    if not replaced:
        # Codex Desktop can keep the rollout file open on Windows, denying
        # rename/delete sharing. Truncating the existing file is less atomic but
        # preserves the live path and keeps the running thread usable.
        try:
            with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(compact_text)
            replaced = True
            append_log(log_path, f"replace_fallback_in_place reason={last_replace_error}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        except Exception:
            raise last_replace_error or PermissionError(str(jsonl_path))

    db_status = reset_db_tokens(db_path, args.thread_id, args.db_reset_tokens, args.max_db_tokens)
    append_log(
        log_path,
        f"auto_compact backup={backup_dir} input_tokens={latest.get('input_tokens')} "
        f"records_before={len(records)} pending_preserved={len(pending_records)} active_gpu={len(active)} {db_status}",
    )
    return backup_dir


def run_once(args: argparse.Namespace, log_path: Path) -> None:
    jsonl_path = Path(args.jsonl_path)
    records, errors = read_jsonl(jsonl_path)
    size_mb = jsonl_path.stat().st_size / (1024 * 1024) if jsonl_path.exists() else 0.0
    if errors:
        append_log(log_path, "read_errors " + "; ".join(errors[:3]))

    latest = get_latest_token_count(records)
    token_text = "input_tokens=none"
    should_compact = False
    if latest:
        token_text = (
            f"input_tokens={latest['input_tokens']} cached={latest['cached_input_tokens']} "
            f"window={latest['model_context_window']} latest_ts={latest.get('timestamp')}"
        )
        should_compact = latest["input_tokens"] >= args.danger_input_tokens

    db_status = reset_db_tokens(Path(args.state_db), args.thread_id, args.db_reset_tokens, args.max_db_tokens)
    append_log(log_path, f"status records={len(records)} jsonl_mb={size_mb:.2f} {token_text} {db_status}")

    if not should_compact:
        return

    pending = pending_tool_calls(records)
    if pending:
        if args.defer_pending_tool_calls:
            append_log(log_path, f"compact_deferred pending_tool_calls={len(pending)} input_tokens={latest['input_tokens']}")
            return
        keep = pending_tool_call_records(records, pending)
        append_log(log_path, f"compact_with_pending pending_tool_calls={len(pending)} preserved={len(keep)} input_tokens={latest['input_tokens']}")
        compact_thread(args, records, latest, log_path, keep)
        return

    compact_thread(args, records, latest, log_path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--jsonl-path", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--state-db", default=str(Path.home() / ".codex" / "state_5.sqlite"))
    parser.add_argument("--session-index", default=str(Path.home() / ".codex" / "session_index.jsonl"))
    parser.add_argument("--live-state", default="")
    parser.add_argument("--log-path", default="")
    parser.add_argument("--danger-input-tokens", type=int, default=115000)
    parser.add_argument("--max-db-tokens", type=int, default=80000)
    parser.add_argument("--db-reset-tokens", type=int, default=20000)
    parser.add_argument("--interval-seconds", type=int, default=8)
    parser.add_argument("--stop-after-minutes", type=float, default=0.0)
    parser.add_argument("--defer-pending-tool-calls", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    if not args.live_state:
        args.live_state = str(workspace / "docs" / "live_run_state.json")
    if not args.log_path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in args.thread_id)
        args.log_path = str(workspace / "run_logs" / f"codex_thread_supervisor_{safe}.log")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    log_path = Path(args.log_path)
    append_log(
        log_path,
        f"start thread={args.thread_id} danger_input_tokens={args.danger_input_tokens} "
        f"interval={args.interval_seconds}s jsonl={args.jsonl_path}",
    )
    started = time.monotonic()
    while True:
        try:
            run_once(args, log_path)
        except Exception as exc:  # pragma: no cover - daemon resilience
            append_log(log_path, f"loop_error {type(exc).__name__}: {exc}")
        if args.once:
            break
        if args.stop_after_minutes > 0 and (time.monotonic() - started) / 60.0 >= args.stop_after_minutes:
            append_log(log_path, "stop elapsed_minutes_reached")
            break
        time.sleep(max(2, args.interval_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
