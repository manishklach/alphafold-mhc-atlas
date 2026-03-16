from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .pilot_usage import aggregate_usage_data
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_repeat_usage(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    df = aggregate_usage_data(config)
    
    out_dir = config.output_dir / "pilot_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if df.empty:
        return {}

    # 1. Active cycles
    cycle_summary = df[df["cycle_id"].notna()].groupby("cycle_id").size().reset_index(name="event_count")
    cycle_path = out_dir / "return_cycle_summary.csv"
    cycle_summary.to_csv(cycle_path, index=False)
    
    # 2. Workflow recurrence
    # How many times was a specific workflow step repeated across cycles?
    workflow_recurrence = df[df["cycle_id"].notna()].groupby(["event_type", "cycle_id"]).size().reset_index(name="count")
    workflow_recurrence = workflow_recurrence.groupby("event_type").size().reset_index(name="num_cycles_active")
    workflow_recurrence_path = out_dir / "recurring_workflow_usage.csv"
    workflow_recurrence.to_csv(workflow_recurrence_path, index=False)

    digest_path = out_dir / "repeat_usage_digest.md"
    lines = [
        f"# Repeat Usage Digest: {config.name}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"- **Active Cycles**: {len(cycle_summary)}",
        f"- **Recurring Workflows**: {len(workflow_recurrence[workflow_recurrence['num_cycles_active'] > 1])}",
        "",
        "## Cycle Engagement",
    ]
    for _, row in cycle_summary.iterrows():
        lines.append(f"- **Cycle {row['cycle_id']}**: {row['event_count']} events")
        
    lines.append("\n## Caveats\nRepeat usage indicates workflow stickiness, not discovery success.")
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "return_cycle_summary.csv": cycle_path,
        "recurring_workflow_usage.csv": workflow_recurrence_path,
        "repeat_usage_digest.md": digest_path
    }
