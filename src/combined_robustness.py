from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_combined_robustness(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    # Analytical Robustness (Phase 17) - Look in various sensitivity subdirs
    # For Phase 18, we expect a summary if it was run.
    # We'll check for robustness_summary.csv in the workspace output or program_memory
    analytical_path = memory_dir / "robustness_summary.csv"
    human_path = memory_dir / "human_robustness_summary.csv"
    
    if not human_path.exists():
        return {}
        
    human_df = safe_read_csv(human_path)
    
    # If analytical is missing, we still want the combined structure
    if not analytical_path.exists():
        # Fallback to empty with columns
        analytical_df = pd.DataFrame(columns=["entity_id", "robustness_label"])
    else:
        analytical_df = safe_read_csv(analytical_path)

    combined = human_df.merge(
        analytical_df[["entity_id", "robustness_label"]].rename(columns={"robustness_label": "analytical_robustness_label"}),
        on="entity_id",
        how="left"
    )
    
    combined["analytical_robustness_label"] = combined["analytical_robustness_label"].fillna("not_available")
    
    def _combined_status(row: pd.Series) -> str:
        h = row["human_robustness_label"]
        a = row["analytical_robustness_label"]
        
        if h == "consensus_robust" and a == "robust_across_playbooks":
            return "strong_candidate_with_human_alignment"
        if h == "disputed_judgment" and a == "robust_across_playbooks":
            return "analytically_stable_but_humanly_disputed"
        if h == "consensus_robust" and a == "fragile_to_assumptions":
            return "analytically_fragile_but_humanly_aligned"
        if h == "disputed_judgment":
            return "requires_more_review"
        return "requires_more_evidence"

    combined["combined_status"] = combined.apply(_combined_status, axis=1)
    
    combined_path = memory_dir / "combined_robustness.csv"
    combined.to_csv(combined_path, index=False)
    
    # Attention queue
    attention_queue = combined[combined["combined_status"].isin(["analytically_stable_but_humanly_disputed", "requires_more_review"])]
    attention_path = memory_dir / "decision_attention_queue.csv"
    attention_queue.to_csv(attention_path, index=False)

    return {
        "combined_robustness.csv": combined_path,
        "decision_attention_queue.csv": attention_path
    }
