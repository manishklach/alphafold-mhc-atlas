from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json
from .project_index import build_project_inventory


def build_project_history(project_dir: Path) -> Path:
    history_dir = project_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    current_snapshot = _current_history_snapshot(project_dir)
    history_path = history_dir / "project_history.json"
    previous = safe_read_json(history_path)
    history_path.write_text(json.dumps(current_snapshot, indent=2), encoding="utf-8")
    _append_decision_history(history_dir / "decision_history.csv", current_snapshot)
    _write_status_timeline(history_dir / "status_timeline.csv", project_dir)
    (history_dir / "change_summary.md").write_text(_build_change_summary(previous, current_snapshot), encoding="utf-8")
    return history_path


def _current_history_snapshot(project_dir: Path) -> dict[str, object]:
    inventory = build_project_inventory(project_dir)
    review_queue_df = safe_read_csv(project_dir / "review" / "review_queue.csv")
    shortlist_df = safe_read_csv(project_dir / "review" / "shortlist.csv")
    feedback_df = safe_read_csv(project_dir / "review" / "feedback_log.csv")
    return {
        "project_name": project_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage": inventory.get("coverage", {}),
        "review_queue_rows": int(len(review_queue_df)),
        "shortlist_rows": int(len(shortlist_df)),
        "feedback_rows": int(len(feedback_df)),
        "handoff_bundle_count": len(list((project_dir / "handoff_bundles").glob("*"))) if (project_dir / "handoff_bundles").exists() else 0,
        "review_packet_count": len(list((project_dir / "review_packets").glob("*"))) if (project_dir / "review_packets").exists() else 0,
        "decision_packet_count": len(list((project_dir / "decision_packets").glob("*"))) if (project_dir / "decision_packets").exists() else 0,
    }


def _append_decision_history(path: Path, snapshot: dict[str, object]) -> None:
    row = {
        "timestamp": snapshot["generated_at"],
        "project_name": snapshot["project_name"],
        "num_variants": snapshot["coverage"].get("num_variants", 0),
        "prioritization_rows": snapshot["coverage"].get("prioritization_rows", 0),
        "review_queue_rows": snapshot["review_queue_rows"],
        "shortlist_rows": snapshot["shortlist_rows"],
        "feedback_rows": snapshot["feedback_rows"],
        "handoff_bundle_count": snapshot["handoff_bundle_count"],
    }
    df = safe_read_csv(path)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def _write_status_timeline(path: Path, project_dir: Path) -> None:
    history_df = safe_read_csv(project_dir / "history" / "decision_history.csv")
    if history_df.empty:
        return
    history_df[["timestamp", "review_queue_rows", "shortlist_rows", "feedback_rows", "handoff_bundle_count"]].to_csv(path, index=False)


def _build_change_summary(previous: dict[str, object], current: dict[str, object]) -> str:
    lines = ["# Change Summary", ""]
    if not previous:
        lines.extend(["- No previous history snapshot was available.", "- This establishes the baseline for future weekly reviews."])
        return "\n".join(lines)
    changes = [
        ("variants", previous.get("coverage", {}).get("num_variants", 0), current.get("coverage", {}).get("num_variants", 0)),
        ("prioritization rows", previous.get("coverage", {}).get("prioritization_rows", 0), current.get("coverage", {}).get("prioritization_rows", 0)),
        ("review queue rows", previous.get("review_queue_rows", 0), current.get("review_queue_rows", 0)),
        ("shortlist rows", previous.get("shortlist_rows", 0), current.get("shortlist_rows", 0)),
        ("feedback rows", previous.get("feedback_rows", 0), current.get("feedback_rows", 0)),
    ]
    for label, old, new in changes:
        delta = new - old
        if delta > 0:
            lines.append(f"- {label}: +{delta} ({old} -> {new})")
        elif delta < 0:
            lines.append(f"- {label}: {delta} ({old} -> {new})")
        else:
            lines.append(f"- {label}: unchanged at {new}")
    return "\n".join(lines)
