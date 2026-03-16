from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .pilot_usage import aggregate_usage_data
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_pilot_health(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    df = aggregate_usage_data(config)
    
    out_dir = config.output_dir / "pilot_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if df.empty:
        return {}

    # Heuristics for health
    num_cycles = df["cycle_id"].nunique() if "cycle_id" in df.columns else 0
    num_roles = df["role_context"].nunique() if "role_context" in df.columns else 0
    workflow_steps = len(df[~df["event_type"].isin(["page_viewed", "workspace_opened"])])
    
    status = "early_signal_only"
    if num_cycles > 2 and workflow_steps > 10:
        status = "workflow_stickiness_emerging"
    elif num_roles > 1:
        status = "promising_but_friction_heavy"

    health_summary = pd.DataFrame([{
        "workspace_id": config.workspace_id,
        "pilot_health_label": status,
        "active_cycles": num_cycles,
        "active_roles": num_roles,
        "workflow_engagement": workflow_steps,
        "last_active": df["timestamp"].max() if not df.empty else "N/A"
    }])
    
    summary_path = out_dir / "pilot_health_summary.csv"
    health_summary.to_csv(summary_path, index=False)
    
    digest_path = out_dir / "pilot_health_digest.md"
    lines = [
        f"# Pilot Health Digest: {config.name}",
        f"Status: **{status.replace('_', ' ').title()}**",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Health Dimensions",
        f"- **Breadth (Roles)**: {num_roles}",
        f"- **Depth (Cycles)**: {num_cycles}",
        f"- **Volume (Steps)**: {workflow_steps}",
        "",
        "## Caveats",
        "Pilot health metrics track process adoption. They are not indicators of biological truth or product fit in broader markets."
    ]
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "pilot_health_summary.csv": summary_path,
        "pilot_health_digest.md": digest_path
    }
