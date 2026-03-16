from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .portfolio_prioritization import build_portfolio_prioritization


def compare_portfolio_modes(
    workspace: WorkspaceConfig | str | Path,
    mode_id_a: str,
    mode_id_b: str
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    # Run both modes
    res_a = build_portfolio_prioritization(config, mode_id_a)
    res_b = build_portfolio_prioritization(config, mode_id_b)
    
    if not res_a or not res_b:
        return {}
        
    df_a = safe_read_csv(res_a["portfolio_prioritization.csv"])
    df_b = safe_read_csv(res_b["portfolio_prioritization.csv"])
    
    merged = df_a[["entity_id", "priority_bucket", "attention_score"]].merge(
        df_b[["entity_id", "priority_bucket", "attention_score"]],
        on="entity_id",
        suffixes=("_a", "_b")
    )
    
    # Filter to only rows where buckets changed
    diff_df = merged[merged["priority_bucket_a"] != merged["priority_bucket_b"]].copy()
    
    out_dir = config.output_dir / "portfolio"
    out_path = out_dir / "portfolio_mode_comparison.csv"
    diff_df.to_csv(out_path, index=False)
    
    md_path = out_dir / "portfolio_comparison_digest.md"
    lines = [
        f"# Portfolio Comparison: {mode_id_a} vs {mode_id_b}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This digest highlights items that shift priority buckets when the team changes capacity constraints or ranking modes.",
        "",
        f"- Items shifted: {len(diff_df)}",
        "",
        "## Top Shifting Items"
    ]
    
    if not diff_df.empty:
        for _, row in diff_df.head(10).iterrows():
            lines.append(f"- **{row['entity_id']}**: {row['priority_bucket_a']} -> {row['priority_bucket_b']}")
            
    lines.extend([
        "",
        "## Caveats",
        "Bucket shifts highlight trade-offs in team capacity and analytical goals. They do not invalidate prior selections."
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "portfolio_mode_comparison.csv": out_path,
        "portfolio_comparison_digest.md": md_path
    }
