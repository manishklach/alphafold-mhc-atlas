from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewPaths:
    project_dir: Path
    root: Path
    notes_dir: Path
    sessions_dir: Path
    handoff_dir: Path
    checklists_dir: Path
    review_queue_csv: Path
    shortlist_csv: Path
    rejected_csv: Path
    review_status_summary_csv: Path
    feedback_log_csv: Path
    feedback_summary_csv: Path
    feedback_by_entity_csv: Path
    feedback_digest_md: Path
    annotations_csv: Path
    pilot_session_json: Path
    next_actions_md: Path
    session_log_jsonl: Path
    session_summary_json: Path
    action_summary_csv: Path
    checklist_runs_csv: Path
    checklist_summary_md: Path
    review_analytics_csv: Path
    feedback_trends_csv: Path
    pilot_usage_summary_md: Path


def get_review_paths(project_dir: Path) -> ReviewPaths:
    root = project_dir / "review"
    return ReviewPaths(
        project_dir=project_dir,
        root=root,
        notes_dir=root / "notes",
        sessions_dir=root / "sessions",
        handoff_dir=project_dir / "handoff_bundles",
        checklists_dir=root / "checklists",
        review_queue_csv=root / "review_queue.csv",
        shortlist_csv=root / "shortlist.csv",
        rejected_csv=root / "rejected_items.csv",
        review_status_summary_csv=root / "review_status_summary.csv",
        feedback_log_csv=root / "feedback_log.csv",
        feedback_summary_csv=root / "feedback_summary.csv",
        feedback_by_entity_csv=root / "feedback_by_entity.csv",
        feedback_digest_md=root / "feedback_digest.md",
        annotations_csv=root / "annotations.csv",
        pilot_session_json=root / "pilot_session.json",
        next_actions_md=root / "next_actions.md",
        session_log_jsonl=root / "session_log.jsonl",
        session_summary_json=root / "session_summary.json",
        action_summary_csv=root / "action_summary.csv",
        checklist_runs_csv=root / "checklists" / "checklist_runs.csv",
        checklist_summary_md=root / "checklists" / "checklist_summary.md",
        review_analytics_csv=root / "review_analytics.csv",
        feedback_trends_csv=root / "feedback_trends.csv",
        pilot_usage_summary_md=root / "pilot_usage_summary.md",
    )


def ensure_review_dirs(project_dir: Path) -> ReviewPaths:
    paths = get_review_paths(project_dir)
    for directory in [paths.root, paths.notes_dir, paths.sessions_dir, paths.handoff_dir, paths.checklists_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return paths
