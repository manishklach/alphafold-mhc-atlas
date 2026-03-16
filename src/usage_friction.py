from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .pilot_usage import aggregate_usage_data
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_usage_friction(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    df = aggregate_usage_data(config)
    
    out_dir = config.output_dir / "pilot_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if df.empty:
        return {}

    # Friction heuristics
    # 1. Repeated page views without workflow steps
    # 2. Abandoned packs (created but never used?) - this requires crossing with other data
    
    # For now, we identify hotspots by event frequency variance or specific "stalled" markers if we added them
    # Simple proxy: high frequency of navigation events vs low frequency of workflow_step events
    
    nav_count = len(df[df["event_type"].isin(["page_viewed", "workspace_opened"])])
    workflow_count = len(df[~df["event_type"].isin(["page_viewed", "workspace_opened"])])
    
    friction_ratio = nav_count / workflow_count if workflow_count > 0 else float('inf')
    
    friction_summary = pd.DataFrame([{
        "metric": "navigation_to_workflow_ratio",
        "value": round(friction_ratio, 2),
        "interpretation": "High ratio may indicate searching/confusion vs execution."
    }])
    
    summary_path = out_dir / "friction_summary.csv"
    friction_summary.to_csv(summary_path, index=False)
    
    digest_path = out_dir / "friction_digest.md"
    lines = [
        f"# Friction Digest: {config.name}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"- **Navigation Events**: {nav_count}",
        f"- **Workflow Steps**: {workflow_count}",
        f"- **Friction Ratio**: {round(friction_ratio, 2)}",
        "",
        "## Observations",
    ]
    if friction_ratio > 10:
        lines.append("- Potential friction hotspot: High navigation-to-workflow ratio. Users may be struggling to find the right next step.")
    else:
        lines.append("- Workflow flow appears stable based on navigation patterns.")
        
    lines.append("\n## Caveats\nFriction is inferred from local usage patterns and is exploratory only.")
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "friction_summary.csv": summary_path,
        "friction_digest.md": digest_path
    }
