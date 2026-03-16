from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_execution_bundle(
    workspace: WorkspaceConfig | str | Path,
    plan_id: str,
    bundle_id: str | None = None
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    bundle_id = bundle_id or f"bundle_{plan_id}_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"

    plan_dir = config.output_dir / "execution_plans" / plan_id
    if not plan_dir.exists():
        raise FileNotFoundError(f"Execution plan '{plan_id}' not found at {plan_dir}")

    bundle_dir = config.output_dir / "execution_bundles" / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy files
    for file_name in ["execution_plan.csv", "followup_tasks.csv"]:
        src = plan_dir / file_name
        if src.exists():
            shutil.copy(src, bundle_dir / file_name)

    # Gather evidence
    tasks_df = safe_read_csv(plan_dir / "followup_tasks.csv")
    selected_variants = set()
    selected_questions = set()
    
    for _, row in tasks_df.iterrows():
        entity_type = row.get("entity_type", "")
        entity_id = row.get("entity_id", "")
        if entity_type in ("shortlist_item", "variant") and entity_id:
            selected_variants.add(entity_id)
        elif entity_type == "open_question" and entity_id:
            selected_questions.add(entity_id)

    # Create dummy files for selected variants and questions
    pd.DataFrame([{"entity_id": v} for v in selected_variants]).to_csv(bundle_dir / "selected_variants.csv", index=False)
    pd.DataFrame([{"question_id": q} for q in selected_questions]).to_csv(bundle_dir / "unresolved_questions.csv", index=False)
    
    pd.DataFrame(columns=["panel_id", "description"]).to_csv(bundle_dir / "selected_panels.csv", index=False)
    pd.DataFrame(columns=["task_id", "dependency_id"]).to_csv(bundle_dir / "dependencies.csv", index=False)
    pd.DataFrame(columns=["task_id", "owner", "owner_role", "notes"]).to_csv(bundle_dir / "owner_assignments.csv", index=False)
    pd.DataFrame(columns=["artifact_path", "description"]).to_csv(bundle_dir / "evidence_manifest.csv", index=False)

    # Create markdown files
    brief_lines = [
        f"# Execution Brief: {bundle_id}",
        f"**Plan ID:** {plan_id}",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## What is being followed up",
        f"- {len(selected_variants)} variants from shortlists",
        f"- {len(selected_questions)} unresolved open questions",
        f"- {len(tasks_df)} actionable tasks",
        "",
        "## Who should review or own what",
        "See `owner_assignments.csv` to assign responsibilities.",
    ]
    (bundle_dir / "execution_brief.md").write_text("\n".join(brief_lines), encoding="utf-8")

    checklist_lines = [
        "# Follow-up Checklist",
        "- [ ] Review tasks in `followup_tasks.csv`",
        "- [ ] Assign owners in `owner_assignments.csv`",
        "- [ ] Execute tasks and capture status",
    ]
    (bundle_dir / "followup_checklist.md").write_text("\n".join(checklist_lines), encoding="utf-8")

    caveat_lines = [
        "# Caveats",
        "This execution bundle organizes downstream experimental and analytical follow-up. Completion of tasks does not automatically validate model predictions or indicate biological truth. Prioritization remains evidence-linked but exploratory.",
    ]
    (bundle_dir / "caveats.md").write_text("\n".join(caveat_lines), encoding="utf-8")

    return bundle_dir
