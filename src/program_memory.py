from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_text
from .decision_history import build_decision_history
from .recurring_patterns import build_recurring_patterns
from .workspace import WorkspaceConfig, load_workspace_config
from .workspace_index import build_workspace_inventory


def build_program_memory(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    config.output_dir.mkdir(parents=True, exist_ok=True)
    memory_dir = config.output_dir / "program_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    inventory = build_workspace_inventory(config)
    decision_outputs = build_decision_history(config)
    pattern_outputs = build_recurring_patterns(config)

    lineage_df = safe_read_csv(decision_outputs["decision_lineage.csv"])
    unresolved_df = safe_read_csv(decision_outputs["unresolved_questions.csv"])
    recurring_patterns_df = safe_read_csv(pattern_outputs["recurring_patterns.csv"])

    recurring_actions_df = _build_workspace_recurring_actions(config)
    attention_queue_df = _build_attention_queue(config, unresolved_df)

    summary_lines = [
        "# Workspace Memory Summary",
        "",
        f"- Workspace: `{config.name}`",
        f"- Projects tracked: {len(inventory['projects'])}",
        f"- Decision lineage rows: {len(lineage_df)}",
        f"- Unresolved questions: {len(unresolved_df)}",
        f"- Recurring pattern rows: {len(recurring_patterns_df)}",
        "",
        "## Top Recurring Themes",
        "",
    ]
    if recurring_patterns_df.empty:
        summary_lines.append("- No recurring patterns were detected yet.")
    else:
        for row in recurring_patterns_df.head(5).to_dict(orient="records"):
            summary_lines.append(f"- `{row.get('pattern_type', 'unknown')}` -> `{row.get('pattern_value', 'unknown')}` ({row.get('count', 0)} occurrences)")
    summary_lines.extend(["", "## Projects Needing Attention", ""])
    if attention_queue_df.empty:
        summary_lines.append("- No projects are currently flagged for attention.")
    else:
        for row in attention_queue_df.head(10).to_dict(orient="records"):
            summary_lines.append(f"- `{row['project_id']}`: {row['reason']}")

    summary_path = memory_dir / "workspace_memory_summary.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    recurring_actions_path = memory_dir / "workspace_recurring_actions.csv"
    attention_queue_path = memory_dir / "workspace_attention_queue.csv"
    recurring_actions_df.to_csv(recurring_actions_path, index=False)
    attention_queue_df.to_csv(attention_queue_path, index=False)

    payload = {
        "workspace": inventory["workspace"],
        "projects": inventory["projects"],
        "summary": inventory["summary"],
        "decision_outputs": {key: str(value) for key, value in decision_outputs.items()},
        "pattern_outputs": {key: str(value) for key, value in pattern_outputs.items()},
        "workspace_memory_summary": str(summary_path),
    }
    memory_json_path = memory_dir / "program_memory.json"
    memory_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame(inventory["projects"]).to_csv(memory_dir / "program_memory_projects.csv", index=False)
    return {
        "program_memory.json": memory_json_path,
        "program_memory_projects.csv": memory_dir / "program_memory_projects.csv",
        "workspace_memory_summary.md": summary_path,
        "workspace_recurring_actions.csv": recurring_actions_path,
        "workspace_attention_queue.csv": attention_queue_path,
        **decision_outputs,
        **pattern_outputs,
    }


def _build_workspace_recurring_actions(config: WorkspaceConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for project in config.projects:
        if not project.path.exists():
            continue
        next_actions_df = safe_read_csv(project.path / "analysis" / "next_action_table.csv")
        for row in next_actions_df.to_dict(orient="records"):
            rows.append(
                {
                    "project_id": project.project_id,
                    "action_type": row.get("action_type"),
                    "priority_level": row.get("priority_level"),
                    "owner_role_suggestion": row.get("owner_role_suggestion"),
                    "status": row.get("status"),
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return (
        df.groupby(["action_type", "priority_level", "owner_role_suggestion", "status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "action_type"], ascending=[False, True])
        .reset_index(drop=True)
    )


def _build_attention_queue(config: WorkspaceConfig, unresolved_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    unresolved_by_project = (
        unresolved_df.groupby("project_id").size().to_dict()
        if not unresolved_df.empty and "project_id" in unresolved_df.columns
        else {}
    )
    for project in config.projects:
        if not project.path.exists():
            rows.append({"project_id": project.project_id, "reason": "Project path is missing.", "urgency": "high"})
            continue
        change_summary = safe_read_text(project.path / "history" / "change_summary.md")
        unresolved_count = int(unresolved_by_project.get(project.project_id, 0))
        if unresolved_count > 0:
            rows.append(
                {
                    "project_id": project.project_id,
                    "reason": f"{unresolved_count} unresolved question(s) remain open.",
                    "urgency": "high" if unresolved_count >= 3 else "medium",
                }
            )
        elif "No previous history snapshot was available." in change_summary:
            rows.append({"project_id": project.project_id, "reason": "Project has only baseline history.", "urgency": "medium"})
    return pd.DataFrame(rows)
