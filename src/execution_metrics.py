from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_execution_metrics(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    plans_dir = config.output_dir / "execution_plans"
    tasks_dfs = []
    if plans_dir.exists():
        for plan_dir in plans_dir.iterdir():
            if plan_dir.is_dir():
                tasks_path = plan_dir / "followup_tasks.csv"
                if tasks_path.exists():
                    tasks_dfs.append(safe_read_csv(tasks_path))
                    
    if tasks_dfs:
        all_tasks_df = pd.concat(tasks_dfs, ignore_index=True)
    else:
        all_tasks_df = pd.DataFrame(columns=["task_id", "status", "owner_role", "notes"])

    if all_tasks_df.empty:
        empty_metrics = pd.DataFrame(columns=["metric", "value"])
        empty_metrics.to_csv(memory_dir / "execution_metrics.csv", index=False)
        empty_metrics.to_csv(memory_dir / "execution_metrics_by_template.csv", index=False)
        empty_metrics.to_csv(memory_dir / "blocked_reasons_summary.csv", index=False)
        md_path = memory_dir / "operational_digest.md"
        md_path.write_text("# Operational Digest\nNo execution data found.", encoding="utf-8")
        return {
            "execution_metrics.csv": memory_dir / "execution_metrics.csv",
            "execution_metrics_by_template.csv": memory_dir / "execution_metrics_by_template.csv",
            "blocked_reasons_summary.csv": memory_dir / "blocked_reasons_summary.csv",
            "operational_digest.md": md_path
        }

    total_tasks = len(all_tasks_df)
    completed_tasks = len(all_tasks_df[all_tasks_df["status"].str.lower() == "completed"])
    blocked_tasks = len(all_tasks_df[all_tasks_df["status"].str.lower() == "blocked"])
    queued_tasks = len(all_tasks_df[all_tasks_df["status"].str.lower().isin(["proposed", "queued"])])
    
    queued_to_completed = queued_tasks / completed_tasks if completed_tasks > 0 else float("inf")
    
    metrics_rows = [
        {"metric": "total_tasks", "value": total_tasks},
        {"metric": "completed_tasks", "value": completed_tasks},
        {"metric": "blocked_tasks", "value": blocked_tasks},
        {"metric": "queued_tasks", "value": queued_tasks},
        {"metric": "queued_to_completed_ratio", "value": round(queued_to_completed, 2)},
    ]
    
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_path = memory_dir / "execution_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    
    roles_df = all_tasks_df.groupby("owner_role", dropna=False).size().reset_index(name="count")
    roles_path = memory_dir / "execution_metrics_by_template.csv"
    roles_df.to_csv(roles_path, index=False)
    
    blocked_df = all_tasks_df[all_tasks_df["status"].str.lower() == "blocked"][["task_id", "notes", "owner_role"]]
    blocked_path = memory_dir / "blocked_reasons_summary.csv"
    blocked_df.to_csv(blocked_path, index=False)
    
    md_path = memory_dir / "operational_digest.md"
    lines = [
        "# Operational Digest",
        f"- Total Tasks: {total_tasks}",
        f"- Completed: {completed_tasks}",
        f"- Blocked: {blocked_tasks}",
        f"- Queued/Proposed: {queued_tasks}",
        "",
        "**Caveat**: Operational completion metrics track follow-through, not scientific validity."
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    
    return {
        "execution_metrics.csv": metrics_path,
        "execution_metrics_by_template.csv": roles_path,
        "blocked_reasons_summary.csv": blocked_path,
        "operational_digest.md": md_path
    }
