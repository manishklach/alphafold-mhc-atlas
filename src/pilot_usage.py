from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .data_access import safe_read_text
from .usage_schema import UsageEvent
from .workspace import WorkspaceConfig, load_workspace_config


def log_pilot_event(
    workspace: WorkspaceConfig | str | Path,
    event_type: str,
    project_id: str | None = None,
    cycle_id: str | None = None,
    role_context: str | None = None,
    surface: str | None = None,
    artifact_id: str | None = None,
    details: dict[str, object] | None = None
) -> None:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    event = UsageEvent(
        event_id=f"evt_{uuid4().hex[:8]}",
        event_type=event_type,
        workspace_id=config.workspace_id,
        project_id=project_id,
        cycle_id=cycle_id,
        role_context=role_context,
        surface=surface,
        artifact_id=artifact_id,
        details=details or {}
    )
    
    log_dir = config.output_dir / "pilot_learning"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "usage_events.jsonl"
    
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def aggregate_usage_data(workspace: WorkspaceConfig | str | Path) -> pd.DataFrame:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    log_file = config.output_dir / "pilot_learning" / "usage_events.jsonl"
    
    if not log_file.exists():
        return pd.DataFrame()
        
    rows = []
    for line in safe_read_text(log_file).splitlines():
        if not line.strip(): continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
            
    return pd.DataFrame(rows)


def summarize_usage(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    df = aggregate_usage_data(config)
    
    out_dir = config.output_dir / "pilot_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if df.empty:
        summary_path = out_dir / "usage_summary.csv"
        pd.DataFrame(columns=["event_type", "count"]).to_csv(summary_path, index=False)
        return {"usage_summary.csv": summary_path}

    summary = df.groupby("event_type").size().reset_index(name="count").sort_values("count", ascending=False)
    summary_path = out_dir / "usage_summary.csv"
    summary.to_csv(summary_path, index=False)
    
    # Workflow usage summary
    if "surface" in df.columns:
        wf_summary = df.groupby("surface").size().reset_index(name="count").sort_values("count", ascending=False)
        wf_path = out_dir / "workflow_usage_summary.csv"
        wf_summary.to_csv(wf_path, index=False)
    
    # Usage digest
    md_path = out_dir / "usage_digest.md"
    lines = [
        f"# Usage Digest: {config.name}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"- **Total Events**: {len(df)}",
        f"- **Unique Sessions/Contexts**: {df['role_context'].nunique() if 'role_context' in df.columns else 0}",
        "",
        "## Event Breakdown",
    ]
    for _, row in summary.iterrows():
        lines.append(f"- **{row['event_type']}**: {row['count']}")
        
    lines.append("\n## Caveats\nUsage data is local and opt-in. It helps identify workflow friction but does not reflect scientific discovery value.")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "usage_summary.csv": summary_path,
        "usage_digest.md": md_path
    }
