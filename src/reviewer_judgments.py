from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import uuid

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def import_reviewer_judgments(
    workspace: WorkspaceConfig | str | Path,
    file_path: Path
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    new_data = safe_read_csv(file_path)
    if new_data.empty:
        raise ValueError(f"No judgment data found in {file_path}")

    # Ensure required columns
    required = ["entity_type", "entity_id", "reviewer_name", "judgment_label"]
    for col in required:
        if col not in new_data.columns:
            raise ValueError(f"Missing required column: {col}")

    memory_dir = config.output_dir / "program_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    log_path = memory_dir / "reviewer_judgments.csv"
    existing = safe_read_csv(log_path)
    
    # Add metadata
    if "judgment_id" not in new_data.columns:
        new_data["judgment_id"] = [f"judg_{uuid.uuid4().hex[:8]}" for _ in range(len(new_data))]
    if "timestamp" not in new_data.columns:
        new_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    if "workspace_id" not in new_data.columns:
        new_data["workspace_id"] = config.workspace_id

    combined = pd.concat([existing, new_data], ignore_index=True) if not existing.empty else new_data
    # Deduplicate by reviewer and entity (keeping latest)
    combined = combined.sort_values("timestamp").drop_duplicates(subset=["entity_type", "entity_id", "reviewer_name"], keep="last")
    
    combined.to_csv(log_path, index=False)
    return log_path


def summarize_judgments(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    log_path = memory_dir / "reviewer_judgments.csv"
    
    df = safe_read_csv(log_path)
    if df.empty:
        summary_path = memory_dir / "reviewer_judgment_summary.csv"
        pd.DataFrame(columns=["entity_type", "entity_id", "num_reviewers", "judgment_distribution"]).to_csv(summary_path, index=False)
        return {"reviewer_judgment_summary.csv": summary_path}

    # Simple group by to see counts
    summary = df.groupby(["entity_type", "entity_id"]).agg(
        num_reviewers=("reviewer_name", "nunique"),
        judgment_distribution=("judgment_label", lambda x: x.value_counts().to_dict())
    ).reset_index()
    
    summary_path = memory_dir / "reviewer_judgment_summary.csv"
    summary.to_csv(summary_path, index=False)
    
    return {"reviewer_judgment_summary.csv": summary_path}
