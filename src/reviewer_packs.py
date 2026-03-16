from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def create_reviewer_pack(
    workspace: WorkspaceConfig | str | Path,
    pack_id: str,
    entity_ids: list[str] | None = None
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    pack_dir = config.output_dir / "reviewer_packs" / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    memory_dir = config.output_dir / "program_memory"
    
    # 1. Entities for Review
    # Pull from most recent multicycle summary or projects
    m_df = safe_read_csv(memory_dir / "multicycle_decision_summary.csv")
    if entity_ids:
        to_review = m_df[m_df["entity_id"].isin(entity_ids)] if not m_df.empty else pd.DataFrame([{"entity_id": eid} for eid in entity_ids])
    else:
        # Default: items in current review cycle
        to_review = m_df.head(20) if not m_df.empty else pd.DataFrame(columns=["entity_id", "current_status"])

    to_review.to_csv(pack_dir / "entities_for_review.csv", index=False)

    # 2. Template
    template_src = Path("data/reviewer_judgment_template.csv")
    if template_src.exists():
        # Pre-fill template if we have entity_ids
        tpl_df = pd.read_csv(template_src)
        rows = []
        for eid in to_review["entity_id"].unique():
            rows.append({
                "entity_type": "variant",
                "entity_id": eid,
                "reviewer_name": "",
                "reviewer_role": "",
                "judgment_label": "",
                "reviewer_confidence": "",
                "rationale_category": "",
                "rationale_text": "",
                "playbook_id": "",
                "benchmark_mode": ""
            })
        pd.DataFrame(rows).to_csv(pack_dir / "judgment_template.csv", index=False)
    
    # 3. Readme
    readme_lines = [
        f"# Reviewer Pack: {pack_id}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Please provide independent judgments for the items in `entities_for_review.csv`.",
        "Fill out `judgment_template.csv` and return it for consensus analysis.",
        "",
        "## Caveats",
        "Independent review is intended to capture diverse expertise. Consensus does not imply biological ground truth."
    ]
    (pack_dir / "reviewer_pack_readme.md").write_text("\n".join(readme_lines), encoding="utf-8")

    return pack_dir
