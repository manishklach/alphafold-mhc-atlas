from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .action_log import ActionLogEntry
from .data_access import safe_read_csv, safe_read_json, safe_read_text
from .review_state import ensure_review_dirs


def start_session(project_dir: Path, reviewer: str | None = None) -> dict[str, object]:
    paths = ensure_review_dirs(project_dir)
    session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    payload = {
        "session_id": session_id,
        "project_name": project_dir.name,
        "reviewer": reviewer or "unspecified",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    paths.session_summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def log_session_action(project_dir: Path, session_id: str, action_type: str, details: dict[str, object] | None = None) -> None:
    paths = ensure_review_dirs(project_dir)
    entry = ActionLogEntry(
        session_id=session_id,
        action_type=action_type,
        project_name=project_dir.name,
        details=details or {},
    )
    with paths.session_log_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.to_dict()) + "\n")
    summarize_session_logs(project_dir)


def summarize_session_logs(project_dir: Path) -> None:
    paths = ensure_review_dirs(project_dir)
    rows = _load_jsonl(paths.session_log_jsonl)
    if not rows:
        return
    df = pd.DataFrame(rows)
    summary = {
        "num_actions": int(len(df)),
        "num_sessions": int(df["session_id"].nunique()) if "session_id" in df.columns else 0,
        "last_action": rows[-1]["action_type"],
        "last_timestamp": rows[-1]["timestamp"],
    }
    existing = safe_read_json(paths.session_summary_json)
    existing.update(summary)
    paths.session_summary_json.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    action_summary = (
        df.groupby("action_type", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    action_summary.to_csv(paths.action_summary_csv, index=False)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in safe_read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
