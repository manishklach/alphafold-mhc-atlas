from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def update_task_status(
    workspace: WorkspaceConfig | str | Path,
    task_id: str,
    status: str,
    notes: str = ""
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    # Locate task in plans
    plans_dir = config.output_dir / "execution_plans"
    if not plans_dir.exists():
        raise FileNotFoundError("No execution plans found.")

    history_log_path = config.output_dir / "program_memory" / "status_history.csv"
    history_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    found = False
    for plan_dir in plans_dir.iterdir():
        if not plan_dir.is_dir():
            continue
        tasks_path = plan_dir / "followup_tasks.csv"
        if not tasks_path.exists():
            continue
            
        tasks_df = safe_read_csv(tasks_path)
        if tasks_df.empty or "task_id" not in tasks_df.columns:
            continue
            
        if task_id in tasks_df["task_id"].values:
            tasks_df["status"] = tasks_df["status"].astype(object)
            tasks_df["notes"] = tasks_df["notes"].astype(object)
            tasks_df.loc[tasks_df["task_id"] == task_id, "status"] = status
            if notes:
                tasks_df.loc[tasks_df["task_id"] == task_id, "notes"] = notes
            tasks_df.to_csv(tasks_path, index=False)
            found = True
            break
            
    if not found:
        raise ValueError(f"Task '{task_id}' not found in any execution plan.")
        
    # Log status update
    new_record = pd.DataFrame([{
        "task_id": task_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes
    }])
    
    existing = safe_read_csv(history_log_path)
    combined = pd.concat([existing, new_record], ignore_index=True) if not existing.empty else new_record
    combined.to_csv(history_log_path, index=False)
    
    return history_log_path
