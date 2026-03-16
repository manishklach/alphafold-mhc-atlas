from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_human_robustness_summary(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    consensus_path = memory_dir / "consensus_summary.csv"
    if not consensus_path.exists():
        return {}
        
    df = safe_read_csv(consensus_path)
    if df.empty:
        return {}

    robustness_results = []
    
    for _, row in df.iterrows():
        level = row["disagreement_level"]
        
        if level == "strong_consensus":
            label = "consensus_robust"
        elif level == "moderate_consensus":
            label = "consensus_fragile"
        elif level == "disputed":
            label = "disputed_judgment"
        else:
            label = "insufficient_data"
            
        robustness_results.append({
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "human_robustness_label": label,
            "num_reviewers": row["num_reviewers"],
            "consensus_label": row["consensus_label"],
            "caution_notes": "Highly disputed item requiring meeting alignment." if label == "disputed_judgment" else ""
        })

    robust_df = pd.DataFrame(robustness_results)
    robust_path = memory_dir / "human_robustness_summary.csv"
    robust_df.to_csv(robust_path, index=False)
    
    # Filter subsets
    robust_df[robust_df["human_robustness_label"] == "consensus_robust"].to_csv(memory_dir / "robust_consensus_items.csv", index=False)
    robust_df[robust_df["human_robustness_label"] == "disputed_judgment"].to_csv(memory_dir / "highly_disputed_items.csv", index=False)

    return {"human_robustness_summary.csv": robust_path}
