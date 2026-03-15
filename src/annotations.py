from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .review_state import ensure_review_dirs


def add_annotation(
    project_dir: Path,
    entity_type: str,
    entity_id: str,
    note_text: str,
    tags: list[str] | None = None,
    reviewer: str = "unspecified",
    category: str = "general",
) -> Path:
    paths = ensure_review_dirs(project_dir)
    note_path = paths.notes_dir / f"{entity_id}.md"
    note_path.write_text(note_text, encoding="utf-8")
    row = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reviewer": reviewer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "tags_serialized": ";".join(tags or []),
        "note_path": str(note_path),
    }
    df = safe_read_csv(paths.annotations_csv)
    df = df[df["entity_id"] != entity_id] if not df.empty and "entity_id" in df.columns else df
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(paths.annotations_csv, index=False)
    return note_path
