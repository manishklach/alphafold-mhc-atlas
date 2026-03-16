from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .data_access import safe_read_csv


def build_org_role_views(workspace_root: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from .org_aggregation import aggregate_organization_data
    data = aggregate_organization_data(workspace_root)
    
    port_df = data["org_portfolio_summary.csv"]
    proj_df = data["org_projects_summary.csv"]
    health_df = data["org_health_baseline.csv"]

    # 1. Manager View
    mgr_path = output_dir / "org_view_manager.md"
    mgr_lines = [
        "# Organization Executive Summary (Manager View)",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Strategic Overview",
        f"- Total active projects across org: {len(proj_df['project_id'].unique()) if not proj_df.empty else 0}",
        f"- Items currently in `do_now`: {len(port_df[port_df['priority_bucket'] == 'do_now']) if not port_df.empty else 0}",
        f"- Items escalating: {len(port_df[port_df['priority_bucket'] == 'escalate']) if not port_df.empty else 0}",
        "",
        "## High Attention Workspaces",
    ]
    if not health_df.empty:
        risks = health_df[health_df["avg_unresolved_carryforward"] > 5]
        if risks.empty:
            mgr_lines.append("- All workspaces show stable workflow metrics.")
        else:
            for ws in risks["workspace_id"].unique():
                mgr_lines.append(f"- **{ws}**: Elevated unresolved carry-forward. May require review capacity adjustment.")
    
    mgr_lines.append("\n## Caveats\nLeadership views emphasize operational flow. They do not validate individual scientific hypotheses.")
    mgr_path.write_text("\n".join(mgr_lines), encoding="utf-8")

    # 2. Comp Lead View
    comp_path = output_dir / "org_view_comp_lead.md"
    comp_lines = [
        "# Organization Operational Health (Comp Lead View)",
        "",
        "## Workflow & Infrastructure",
        f"- Workspaces aggregated: {len(port_df['workspace_id'].unique()) if not port_df.empty else 0}",
        "",
        "## Systemic Bottlenecks",
    ]
    if not port_df.empty:
        blocked = port_df[port_df["current_execution_status"] == "blocked"]
        comp_lines.append(f"- Total blocked items across org: {len(blocked)}")
        
    comp_path.write_text("\n".join(comp_lines), encoding="utf-8")

    return {
        "org_view_manager.md": mgr_path,
        "org_view_comp_lead.md": comp_path
    }
