from __future__ import annotations

from pathlib import Path

from .data_access import safe_read_csv
from .review_queue import summarize_review_state
from .review_state import ensure_review_dirs


def refresh_shortlists(project_dir: Path) -> Path:
    paths = ensure_review_dirs(project_dir)
    summarize_review_state(project_dir)
    return paths.shortlist_csv


def shortlist_count(project_dir: Path) -> int:
    paths = ensure_review_dirs(project_dir)
    shortlist_df = safe_read_csv(paths.shortlist_csv)
    return int(len(shortlist_df))
