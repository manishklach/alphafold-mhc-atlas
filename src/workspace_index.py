from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .project_index import build_project_inventory
from .workspace import WorkspaceConfig, load_workspace_config


def build_workspace_inventory(workspace: WorkspaceConfig | str | Path) -> dict[str, object]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    rows: list[dict[str, object]] = []
    notes: list[str] = []
    for project in config.projects:
        exists = project.path.exists()
        inventory = build_project_inventory(project.path) if exists else {}
        coverage = inventory.get("coverage", {}) if inventory else {}
        rows.append(
            {
                "workspace_id": config.workspace_id,
                "project_id": project.project_id,
                "project_path": str(project.path),
                "project_status": "available" if exists else "missing",
                "num_alleles": int(coverage.get("num_alleles", 0)),
                "num_variants": int(coverage.get("num_variants", 0)),
                "prediction_coverage": int(coverage.get("prediction_coverage", 0)),
                "structure_coverage": int(coverage.get("structural_coverage", 0)),
                "prioritization_coverage": int(coverage.get("prioritization_rows", 0)),
                "review_status": _review_status(inventory),
                "last_updated": inventory.get("snapshot", {}).get("generated_at") if inventory else None,
                "notes": "; ".join(project.tags + ([project.notes] if project.notes else [])),
                "tags_serialized": ";".join(project.tags),
            }
        )
        if not exists:
            notes.append(f"Missing project path: {project.path}")

    projects_df = pd.DataFrame(rows)
    summary_df = pd.DataFrame(
        [
            {
                "workspace_id": config.workspace_id,
                "workspace_name": config.name,
                "num_projects": int(len(projects_df)),
                "num_available_projects": int((projects_df["project_status"] == "available").sum()) if not projects_df.empty else 0,
                "total_variants": int(projects_df["num_variants"].sum()) if not projects_df.empty else 0,
                "total_alleles": int(projects_df["num_alleles"].sum()) if not projects_df.empty else 0,
                "projects_with_review": int((projects_df["review_status"] != "not_started").sum()) if not projects_df.empty else 0,
            }
        ]
    )
    return {
        "workspace": config.to_dict(),
        "projects": rows,
        "summary": summary_df.to_dict(orient="records"),
        "notes": notes,
    }


def write_workspace_inventory(workspace: WorkspaceConfig | str | Path) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    config.output_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_workspace_inventory(config)
    output_path = config.output_dir / "workspace_inventory.json"
    output_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    pd.DataFrame(inventory["projects"]).to_csv(config.output_dir / "workspace_projects.csv", index=False)
    pd.DataFrame(inventory["summary"]).to_csv(config.output_dir / "workspace_summary.csv", index=False)
    return output_path


def _review_status(inventory: dict[str, object]) -> str:
    coverage = inventory.get("coverage", {})
    if int(coverage.get("shortlist_rows", 0)) > 0:
        return "shortlisted"
    if int(coverage.get("review_queue_rows", 0)) > 0:
        return "in_review"
    return "not_started"
