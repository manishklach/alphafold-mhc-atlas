from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json
from .review_state import ensure_review_dirs
from .session_logging import start_session


def initialize_pilot_workflow(project_dir: Path, scenario_id: str, reviewer: str = "unspecified") -> Path:
    paths = ensure_review_dirs(project_dir)
    session = start_session(project_dir, reviewer=reviewer)
    payload = {
        "project_name": project_dir.name,
        "scenario_id": scenario_id,
        "reviewer": reviewer,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session["session_id"],
        "status": "initialized",
    }
    paths.pilot_session_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    paths.next_actions_md.write_text(
        "\n".join(
            [
                "# Next Actions",
                "",
                "- Review ranked variants and evidence coverage.",
                "- Mark shortlisted or uncertain items in the review queue.",
                "- Capture feedback and biological caveats before export.",
            ]
        ),
        encoding="utf-8",
    )
    return paths.pilot_session_json


def build_review_analytics(project_dir: Path) -> None:
    paths = ensure_review_dirs(project_dir)
    review_df = safe_read_csv(paths.review_queue_csv)
    feedback_df = safe_read_csv(paths.feedback_log_csv)
    action_df = safe_read_csv(paths.action_summary_csv)

    analytics_rows: list[dict[str, object]] = []
    if not review_df.empty:
        analytics_rows.append(
            {
                "metric": "most_reviewed_status",
                "value": review_df["review_status"].value_counts(dropna=False).idxmax(),
            }
        )
        analytics_rows.append(
            {
                "metric": "shortlisted_count",
                "value": int(review_df["review_status"].isin(["shortlisted", "report_inclusion", "experimental_followup"]).sum()),
            }
        )
    if not feedback_df.empty and "concern_type" in feedback_df.columns:
        analytics_rows.append(
            {
                "metric": "most_common_concern_type",
                "value": feedback_df["concern_type"].value_counts(dropna=False).idxmax(),
            }
        )
    if not action_df.empty and "action_type" in action_df.columns:
        analytics_rows.append(
            {
                "metric": "most_common_action",
                "value": action_df.sort_values("count", ascending=False).iloc[0]["action_type"],
            }
        )
    pd.DataFrame(analytics_rows).to_csv(paths.review_analytics_csv, index=False)

    lines = [
        "# Pilot Usage Summary",
        "",
        f"- Review queue rows: {len(review_df)}",
        f"- Feedback entries: {len(feedback_df)}",
        f"- Logged actions: {int(action_df['count'].sum()) if not action_df.empty and 'count' in action_df.columns else 0}",
    ]
    paths.pilot_usage_summary_md.write_text("\n".join(lines), encoding="utf-8")
