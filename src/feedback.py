from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .feedback_schema import FeedbackEntry
from .review_state import ensure_review_dirs


def add_feedback(project_dir: Path, entry: FeedbackEntry) -> Path:
    paths = ensure_review_dirs(project_dir)
    df = safe_read_csv(paths.feedback_log_csv)
    df = pd.concat([df, pd.DataFrame([entry.to_dict()])], ignore_index=True)
    df.to_csv(paths.feedback_log_csv, index=False)
    summarize_feedback(project_dir)
    return paths.feedback_log_csv


def summarize_feedback(project_dir: Path) -> None:
    paths = ensure_review_dirs(project_dir)
    feedback_df = safe_read_csv(paths.feedback_log_csv)
    if feedback_df.empty:
        return

    summary = (
        feedback_df.groupby("concern_type", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    summary.to_csv(paths.feedback_summary_csv, index=False)

    by_entity = (
        feedback_df.groupby(["entity_type", "entity_id"], dropna=False)
        .agg(
            num_feedback=("feedback_id", "count"),
            mean_usefulness_rating=("usefulness_rating", "mean"),
            mean_clarity_rating=("clarity_rating", "mean"),
        )
        .reset_index()
        .sort_values("num_feedback", ascending=False)
        .reset_index(drop=True)
    )
    by_entity.to_csv(paths.feedback_by_entity_csv, index=False)

    digest_lines = [
        "# Feedback Digest",
        "",
        f"- Total feedback entries: {len(feedback_df)}",
        f"- Unique reviewers: {feedback_df['reviewer_name'].nunique() if 'reviewer_name' in feedback_df.columns else 0}",
    ]
    if not summary.empty:
        digest_lines.append(f"- Most common concern: {summary.iloc[0]['concern_type']}")
    digest_lines.extend(
        [
            "",
            "Feedback in this project is descriptive pilot-user input. It is not treated as biological validation.",
        ]
    )
    paths.feedback_digest_md.write_text("\n".join(digest_lines), encoding="utf-8")


def build_feedback_trends(project_dir: Path) -> None:
    paths = ensure_review_dirs(project_dir)
    feedback_df = safe_read_csv(paths.feedback_log_csv)
    if feedback_df.empty:
        return
    trends = (
        feedback_df.groupby(["entity_type", "concern_type"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    trends.to_csv(paths.feedback_trends_csv, index=False)
