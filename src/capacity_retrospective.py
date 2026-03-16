from __future__ import annotations

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from .data_access import safe_read_csv


def build_org_capacity_retrospective(workspace_root: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from .org_aggregation import aggregate_organization_data
    data = aggregate_organization_data(workspace_root)
    
    port_df = data["org_portfolio_summary.csv"]
    
    if port_df.empty or "priority_bucket" not in port_df.columns:
        return {}

    # 1. Bucket distribution across workspaces
    capacity_df = port_df.groupby(["workspace_id", "priority_bucket"]).size().reset_index(name="count")
    capacity_path = output_dir / "org_capacity_distribution.csv"
    capacity_df.to_csv(capacity_path, index=False)
    
    # 2. Queue trends (mocking time component for Phase 20 if history is sparse)
    # In a real system, we'd pull from historical aggregation snapshots
    # For this implementation, we summarize current queue state as a baseline
    
    digest_path = output_dir / "capacity_retrospective_digest.md"
    lines = [
        "# Organization Capacity Retrospective",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Capacity Allocation by Workspace",
    ]
    for ws_id, group in capacity_df.groupby("workspace_id"):
        lines.append(f"### {ws_id}")
        for _, row in group.iterrows():
            lines.append(f"- **{row['priority_bucket']}**: {row['count']}")
            
    lines.extend([
        "",
        "## Caveats",
        "Capacity trends reflect operational throughput, not scientific accuracy."
    ])
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "org_capacity_distribution.csv": capacity_path,
        "capacity_retrospective_digest.md": digest_path
    }
