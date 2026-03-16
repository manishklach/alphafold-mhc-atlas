from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import yaml

import pandas as pd

from .data_access import safe_read_csv
from .resource_paths import repo_or_resource_path
from .workspace import WorkspaceConfig, load_workspace_config


def run_execution_checklist(
    workspace: WorkspaceConfig | str | Path,
    template_id: str,
    plan_id: str,
    reviewer: str = "pilot_user"
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    path = repo_or_resource_path("data", "execution_checklists.yaml")
    if not path.exists():
        raise FileNotFoundError("Execution checklists not found.")
        
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("templates", []) if isinstance(payload, dict) else []
    
    target = None
    for t in templates:
        if t.get("template_id") == template_id:
            target = t
            break
            
    if not target:
        raise ValueError(f"Execution checklist template '{template_id}' not found.")

    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    runs_path = output_dir / "execution_checklist_runs.csv"
    
    rows = []
    timestamp = datetime.now(timezone.utc).isoformat()
    for item in target.get("items", []):
        rows.append({
            "run_timestamp": timestamp,
            "template_id": template_id,
            "plan_id": plan_id,
            "reviewer": reviewer,
            "checklist_item": item,
            "status": "checked"
        })
        
    new_df = pd.DataFrame(rows)
    existing = safe_read_csv(runs_path)
    combined = pd.concat([existing, new_df], ignore_index=True) if not existing.empty else new_df
    combined.to_csv(runs_path, index=False)
    
    return runs_path
