from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from .data_access import safe_read_csv
from .resource_paths import repo_or_resource_path
from .review_state import ensure_review_dirs


def load_checklist_templates(path: Path | None = None) -> dict[str, object]:
    template_path = path or repo_or_resource_path("data", "checklist_templates.yaml")
    if not template_path.exists():
        return {"templates": []}
    return yaml.safe_load(template_path.read_text(encoding="utf-8")) or {"templates": []}


def run_checklist(project_dir: Path, template_name: str, reviewer: str = "unspecified") -> Path:
    paths = ensure_review_dirs(project_dir)
    payload = load_checklist_templates()
    templates = payload.get("templates", [])
    template = next((item for item in templates if item.get("template_id") == template_name), None)
    if template is None:
        raise ValueError(f"Checklist template not found: {template_name}")

    rows = []
    timestamp = datetime.now(timezone.utc).isoformat()
    for item in template.get("items", []):
        rows.append(
            {
                "template_id": template_name,
                "item_id": item.get("item_id", ""),
                "description": item.get("description", ""),
                "status": "pending",
                "reviewer": reviewer,
                "timestamp": timestamp,
            }
        )
    pd.DataFrame(rows).to_csv(paths.checklist_runs_csv, index=False)
    summary_lines = [
        f"# Checklist Run: {template_name}",
        "",
        f"- Reviewer: {reviewer}",
        f"- Items: {len(rows)}",
        "- Checklist items are prompts for structured review, not proof of scientific validity.",
    ]
    paths.checklist_summary_md.write_text("\n".join(summary_lines), encoding="utf-8")
    return paths.checklist_runs_csv
