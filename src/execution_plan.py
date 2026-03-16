from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .execution_templates import get_execution_template, ExecutionTemplate


def build_execution_plan(
    workspace: WorkspaceConfig | str | Path,
    template_id: str,
    plan_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    template = get_execution_template(template_id)
    plan_id = plan_id or f"plan_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"

    output_dir = config.output_dir / "execution_plans" / plan_id
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[dict[str, object]] = []
    plan_entities: list[dict[str, object]] = []
    
    for project in config.projects:
        if not project.path.exists():
            continue
        
        # Load inputs
        shortlist_df = safe_read_csv(project.path / "review" / "shortlist.csv")
        next_actions_df = safe_read_csv(project.path / "analysis" / "next_action_table.csv")
        open_qs_df = safe_read_csv(project.path / "analysis" / "open_questions.csv")

        # Process shortlists -> follow up
        if not shortlist_df.empty:
            for _, row in shortlist_df.iterrows():
                entity_id = row.get("entity_id") or row.get("variant_id")
                if not entity_id:
                    continue
                plan_entities.append({"plan_id": plan_id, "entity_type": "shortlist_item", "entity_id": entity_id, "project_id": project.project_id})
                
                for task_type in template.default_task_types:
                    task_id = f"task_{uuid.uuid4().hex[:8]}"
                    tasks.append({
                        "task_id": task_id,
                        "plan_id": plan_id,
                        "project_id": project.project_id,
                        "workspace_id": config.workspace_id,
                        "entity_type": "shortlist_item",
                        "entity_id": entity_id,
                        "task_type": task_type,
                        "task_title": f"{task_type.replace('_', ' ').title()} for {entity_id}",
                        "rationale": row.get("rationale", ""),
                        "linked_evidence": "review/shortlist.csv",
                        "owner": "",
                        "owner_role": template.default_role_suggestions.get(task_type, "unassigned"),
                        "status": "proposed",
                        "due_date": "",
                        "dependency_ids_serialized": "",
                        "source_cycle_id": "current",
                        "priority_level": "medium",
                        "notes": ""
                    })

        # Process next actions
        if not next_actions_df.empty:
            for _, row in next_actions_df.iterrows():
                entity_id = row.get("entity_id")
                if not entity_id:
                    continue
                tasks.append({
                    "task_id": f"task_{uuid.uuid4().hex[:8]}",
                    "plan_id": plan_id,
                    "project_id": project.project_id,
                    "workspace_id": config.workspace_id,
                    "entity_type": "next_action",
                    "entity_id": entity_id,
                    "task_type": row.get("action_type", "gather_more_evidence"),
                    "task_title": f"Next action for {entity_id}",
                    "rationale": row.get("rationale", ""),
                    "linked_evidence": "analysis/next_action_table.csv",
                    "owner": "",
                    "owner_role": row.get("owner_role_suggestion", "unassigned"),
                    "status": "proposed",
                    "due_date": "",
                    "dependency_ids_serialized": "",
                    "source_cycle_id": "current",
                    "priority_level": "medium",
                    "notes": ""
                })

        # Process open questions
        if not open_qs_df.empty:
            for _, row in open_qs_df.iterrows():
                question_id = row.get("question_id")
                if not question_id:
                    continue
                plan_entities.append({"plan_id": plan_id, "entity_type": "open_question", "entity_id": question_id, "project_id": project.project_id})

    tasks_df = pd.DataFrame(tasks)
    entities_df = pd.DataFrame(plan_entities)
    
    tasks_path = output_dir / "followup_tasks.csv"
    entities_path = output_dir / "execution_plan.csv"
    
    if not tasks_df.empty:
        tasks_df.to_csv(tasks_path, index=False)
    else:
        pd.DataFrame(columns=[
            "task_id", "plan_id", "project_id", "workspace_id", "entity_type", "entity_id",
            "task_type", "task_title", "rationale", "linked_evidence", "owner", "owner_role",
            "status", "due_date", "dependency_ids_serialized", "source_cycle_id", "priority_level", "notes"
        ]).to_csv(tasks_path, index=False)

    if not entities_df.empty:
        entities_df.to_csv(entities_path, index=False)
    else:
        pd.DataFrame(columns=["plan_id", "entity_type", "entity_id", "project_id"]).to_csv(entities_path, index=False)
        
    summary_path = output_dir / "execution_plan_summary.md"
    lines = [
        f"# Execution Plan: {plan_id}",
        f"- Template: {template.label}",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Total Tasks: {len(tasks)}",
        f"- Total Entities: {len(plan_entities)}",
        "",
        "## Caveats",
        "This is an operational plan derived from structural analysis. Tasks do not validate the model predictions but help coordinate next experimental or analytical steps.",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "execution_plan.csv": entities_path,
        "followup_tasks.csv": tasks_path,
        "execution_plan_summary.md": summary_path,
        "plan_dir": output_dir
    }
