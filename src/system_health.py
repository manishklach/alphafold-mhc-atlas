from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .data_access import safe_read_csv


def build_org_system_health(workspace_root: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from .org_aggregation import aggregate_organization_data
    data = aggregate_organization_data(workspace_root)
    
    health_df = data["org_health_baseline.csv"]
    port_df = data["org_portfolio_summary.csv"]
    
    health_results = []
    
    if not health_df.empty:
        for ws_id, group in health_df.groupby("workspace_id"):
            avg_unres = group["avg_unresolved_carryforward"].mean() if "avg_unresolved_carryforward" in group.columns else 0
            
            status = "stable"
            if avg_unres > 5: status = "unresolved_burden_risk"
            
            health_results.append({
                "workspace_id": ws_id,
                "avg_unresolved": round(avg_unres, 2),
                "health_category": status
            })
            
    summary_df = pd.DataFrame(health_results)
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=["workspace_id", "avg_unresolved", "health_category"])
    
    summary_path = output_dir / "org_system_health_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    # Attention risk queue
    risk_df = summary_df[summary_df["health_category"] != "stable"]
    risk_path = output_dir / "org_attention_risk_queue.csv"
    risk_df.to_csv(risk_path, index=False)
    
    digest_path = output_dir / "health_digest.md"
    lines = [
        "# Organization Decision-System Health",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Workspace Health Status",
    ]
    if summary_df.empty:
        lines.append("- No health data aggregated.")
    else:
        for _, row in summary_df.iterrows():
            lines.append(f"- **{row['workspace_id']}**: {row['health_category']} (Avg Unresolved: {row['avg_unresolved']})")
            
    lines.extend([
        "",
        "## Caveats",
        "Workflow health metrics are descriptive indicators of process continuity, not scientific validation."
    ])
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "org_system_health_summary.csv": summary_path,
        "org_attention_risk_queue.csv": risk_path,
        "health_digest.md": digest_path
    }
