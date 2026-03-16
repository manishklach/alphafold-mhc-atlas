from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .pilot_usage import aggregate_usage_data
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_workflow_adoption(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    df = aggregate_usage_data(config)
    
    out_dir = config.output_dir / "pilot_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if df.empty:
        return {}

    # 1. Adoption by surface (UI vs CLI)
    surface_df = df.groupby("surface").size().reset_index(name="count")
    surface_path = out_dir / "surface_adoption.csv"
    surface_df.to_csv(surface_path, index=False)
    
    # 2. Workflow adoption (event types)
    workflow_df = df.groupby("event_type").size().reset_index(name="count")
    workflow_path = out_dir / "workflow_adoption.csv"
    workflow_df.to_csv(workflow_path, index=False)
    
    # 3. Role workflow adoption
    role_df = df[df["role_context"].notna()].groupby("role_context").size().reset_index(name="count")
    role_path = out_dir / "role_workflow_adoption.csv"
    role_df.to_csv(role_path, index=False)

    digest_path = out_dir / "adoption_digest.md"
    lines = [
        f"# Workflow Adoption Digest: {config.name}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Surface Usage",
    ]
    for _, row in surface_df.iterrows():
        lines.append(f"- **{row['surface']}**: {row['count']} events")
        
    lines.append("\n## Top Workflow Events")
    for _, row in workflow_df.sort_values("count", ascending=False).head(5).iterrows():
        lines.append(f"- **{row['event_type']}**: {row['count']} occurrences")

    lines.append("\n## Caveats\nAdoption metrics track engagement frequency, not scientific correctness or impact.")
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "workflow_adoption.csv": workflow_path,
        "role_workflow_adoption.csv": role_path,
        "adoption_digest.md": digest_path
    }
