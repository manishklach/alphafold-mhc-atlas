from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import uuid

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_portfolio_aggregation(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    # 1. Gather combined robustness (primary source of portfolio candidates in Phase 19)
    # This brings in variants that have been tracked in Phase 18
    combined_path = memory_dir / "combined_robustness.csv"
    if combined_path.exists():
        combined_df = safe_read_csv(combined_path)
    else:
        combined_df = pd.DataFrame(columns=["entity_id", "analytical_robustness_label", "human_robustness_label", "combined_status"])
        
    # 2. Gather multicycle history (for project/cycle lineage)
    history_path = memory_dir / "multicycle_decision_summary.csv"
    if history_path.exists():
        history_df = safe_read_csv(history_path)
    else:
        history_df = pd.DataFrame(columns=["entity_id", "project_id", "latest_seen_review", "current_status"])

    # 3. Merge
    if not combined_df.empty:
        merged = combined_df.merge(
            history_df[["entity_id", "project_id", "latest_seen_review", "current_status"]],
            on="entity_id",
            how="left"
        )
    else:
        merged = pd.DataFrame(columns=[
            "entity_id", "analytical_robustness_label", "human_robustness_label", 
            "combined_status", "project_id", "latest_seen_review", "current_status"
        ])

    rows = []
    for _, row in merged.iterrows():
        eid = row.get("entity_id", "unknown")
        rows.append({
            "portfolio_item_id": f"port_{uuid.uuid4().hex[:8]}",
            "source_workspace_id": config.workspace_id,
            "source_project_id": row.get("project_id", "multiple"),
            "entity_type": "variant",
            "entity_id": eid,
            "analytical_robustness_label": row.get("analytical_robustness_label", "unknown"),
            "human_robustness_label": row.get("human_robustness_label", "unknown"),
            "consensus_status": row.get("combined_status", "unknown"),
            "current_execution_status": row.get("current_status", "unknown")
        })

    out_df = pd.DataFrame(rows)
    out_dir = config.output_dir / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / "portfolio_candidates.csv"
    out_df.to_csv(out_path, index=False)
    
    # Simple markdown summary
    md_path = out_dir / "portfolio_candidates_summary.md"
    lines = [
        f"# Portfolio Aggregation: {config.name}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"- **Total Candidates**: {len(out_df)}",
        "- **Sources**: Aggregated from multicycle memory and combined robustness summaries.",
        "",
        "## Caveats",
        "Portfolio candidates are structural hypotheses awaiting experimental execution, not validated results."
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "portfolio_candidates.csv": out_path,
        "portfolio_candidates_summary.md": md_path
    }
