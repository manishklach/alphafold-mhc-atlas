from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_consensus_summaries(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    log_path = memory_dir / "reviewer_judgments.csv"
    
    df = safe_read_csv(log_path)
    if df.empty:
        return {}

    results = []
    
    # Group by entity
    for (etype, eid), group in df.groupby(["entity_type", "entity_id"]):
        counts = group["judgment_label"].value_counts()
        total = len(group)
        top_label = counts.index[0]
        top_count = counts.iloc[0]
        
        # Heuristic for disagreement
        if total == 1:
            level = "insufficient_reviewer_coverage"
        elif top_count == total:
            level = "strong_consensus"
        elif top_count / total >= 0.7:
            level = "moderate_consensus"
        elif top_count / total >= 0.5:
            level = "mixed_judgment"
        else:
            level = "disputed"
            
        results.append({
            "entity_type": etype,
            "entity_id": eid,
            "num_reviewers": total,
            "reviewer_roles": ";".join(sorted(group["reviewer_role"].dropna().unique())),
            "judgment_distribution": counts.to_dict(),
            "consensus_label": top_label if level != "disputed" else "no_consensus",
            "disagreement_level": level,
            "confidence_spread": group["reviewer_confidence"].dropna().unique().tolist()
        })

    summary_df = pd.DataFrame(results)
    summary_path = memory_dir / "consensus_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    disputed_path = memory_dir / "disputed_items.csv"
    summary_df[summary_df["disagreement_level"].isin(["disputed", "mixed_judgment"])].to_csv(disputed_path, index=False)
    
    consensus_path = memory_dir / "consensus_items.csv"
    summary_df[summary_df["disagreement_level"].isin(["strong_consensus", "moderate_consensus"])].to_csv(consensus_path, index=False)

    return {
        "consensus_summary.csv": summary_path,
        "disputed_items.csv": disputed_path,
        "consensus_items.csv": consensus_path
    }
