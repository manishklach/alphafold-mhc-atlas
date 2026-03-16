from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def create_consensus_meeting_pack(
    workspace: WorkspaceConfig | str | Path,
    meeting_id: str
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    meeting_dir = config.output_dir / "consensus_meetings" / meeting_id
    meeting_dir.mkdir(parents=True, exist_ok=True)

    memory_dir = config.output_dir / "program_memory"
    
    # 1. Gather summaries
    files_to_copy = [
        "consensus_summary.csv",
        "disputed_items.csv",
        "disagreement_drivers.csv",
        "combined_robustness.csv",
        "decision_attention_queue.csv"
    ]
    for f in files_to_copy:
        src = memory_dir / f
        if src.exists():
            shutil.copy(src, meeting_dir / f)

    # 2. Consensus Brief
    brief_path = meeting_dir / "consensus_brief.md"
    
    disputed_df = safe_read_csv(memory_dir / "disputed_items.csv")
    combined_df = safe_read_csv(memory_dir / "combined_robustness.csv")
    
    lines = [
        f"# Consensus Meeting Brief: {meeting_id}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Meeting Objectives",
        "1. Review items with strong human disagreement.",
        "2. Align on follow-up for analytically stable but humanly disputed items.",
        "3. Confirm priorities for consensus-backed robust items.",
        "",
        "## Summary of Divergence",
        f"- Items with consensus: {len(combined_df[combined_df['human_robustness_label'] == 'consensus_robust']) if not combined_df.empty else 0}",
        f"- Items requiring discussion: {len(disputed_df) if not disputed_df.empty else 0}",
        "",
        "## High Priority Disagreement",
        "Items that are analytically robust but have disputed human judgments:"
    ]
    
    if not combined_df.empty:
        stable_disputed = combined_df[combined_df["combined_status"] == "analytically_stable_but_humanly_disputed"]
        for _, row in stable_disputed.iterrows():
            lines.append(f"- **{row['entity_id']}**: Analytical Robustness: {row['analytical_robustness_label']}")
            
    lines.extend([
        "",
        "## Caveats",
        "Reviewer consensus captures team judgment, not biological truth. Decisions should be made while maintaining explicit awareness of model uncertainty."
    ])
    
    brief_path.write_text("\n".join(lines), encoding="utf-8")

    return meeting_dir
