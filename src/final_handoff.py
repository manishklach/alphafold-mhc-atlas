from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .executive_brief import generate_executive_brief


def build_final_handoff(
    workspace: WorkspaceConfig | str | Path,
    handoff_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    handoff_id = handoff_id or f"final_handoff_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"

    output_dir = config.output_dir / "final_handoffs" / handoff_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    memory_dir = config.output_dir / "program_memory"

    # 1. Generate Executive Brief directly into the handoff dir
    brief_res = generate_executive_brief(config, handoff_id)
    shutil.copy(brief_res["executive_brief.md"], output_dir / "executive_brief.md")
    
    # 2. Extract consensus robust candidates
    combined_path = memory_dir / "combined_robustness.csv"
    if combined_path.exists():
        combined_df = safe_read_csv(combined_path)
        candidates = combined_df[combined_df["combined_status"] == "strong_candidate_with_human_alignment"]
        candidates.to_csv(output_dir / "consensus_robust_candidates.csv", index=False)
    else:
        pd.DataFrame(columns=["entity_id", "combined_status"]).to_csv(output_dir / "consensus_robust_candidates.csv", index=False)

    # 3. Create generic evidence manifest mapping back to project directories
    # Note: A real implementation would pull specific bundle files, but for the Phase 19 requirement we establish the auditable link
    manifest_lines = [
        "entity_id,artifact_type,expected_location",
    ]
    if combined_path.exists() and not candidates.empty:
        for eid in candidates["entity_id"]:
            manifest_lines.append(f"{eid},structural_summary,analysis/summary.csv")
            manifest_lines.append(f"{eid},reviewer_judgments,program_memory/reviewer_judgments.csv")
            
    (output_dir / "evidence_manifest.csv").write_text("\n".join(manifest_lines), encoding="utf-8")

    # 4. Caveats
    caveats_lines = [
        "# Caveats and Limitations",
        "",
        "This handoff bundle represents the final operational output of the Phase 19 review cycle.",
        "",
        "1. **Exploratory Only**: Candidates are structural hypotheses, not validated binders.",
        "2. **Human Judgment**: Consensus indicates team alignment, not biological proof.",
        "3. **Analytical Robustness**: Mathematical stability under different filters does not guarantee physical binding.",
        "",
        "Proceed with targeted experimental validation."
    ]
    (output_dir / "caveats_and_limitations.md").write_text("\n".join(caveats_lines), encoding="utf-8")

    return {
        "executive_brief.md": output_dir / "executive_brief.md",
        "consensus_robust_candidates.csv": output_dir / "consensus_robust_candidates.csv",
        "evidence_manifest.csv": output_dir / "evidence_manifest.csv",
        "caveats_and_limitations.md": output_dir / "caveats_and_limitations.md",
        "handoff_dir": output_dir
    }
