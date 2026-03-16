from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import yaml

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .resource_paths import repo_or_resource_path


def generate_executive_brief(
    workspace: WorkspaceConfig | str | Path,
    brief_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    brief_id = brief_id or f"exec_brief_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"
    
    output_dir = config.output_dir / "executive_briefs" / brief_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    memory_dir = config.output_dir / "program_memory"
    combined_path = memory_dir / "combined_robustness.csv"
    
    if combined_path.exists():
        combined_df = safe_read_csv(combined_path)
    else:
        combined_df = pd.DataFrame(columns=["entity_id", "combined_status"])
        
    template_path = repo_or_resource_path("data", "executive_brief_template.yaml")
    if template_path.exists():
        template_data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    else:
        template_data = {"sections": []}
        
    brief_path = output_dir / "executive_brief.md"
    lines = [
        f"# Executive Brief: {config.name}",
        f"**Brief ID**: {brief_id}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        ""
    ]
    
    strong_candidates = combined_df[combined_df["combined_status"] == "strong_candidate_with_human_alignment"] if not combined_df.empty else pd.DataFrame()
    disputed_candidates = combined_df[combined_df["combined_status"] == "analytically_stable_but_humanly_disputed"] if not combined_df.empty else pd.DataFrame()

    for sec in template_data.get("sections", []):
        sid = sec.get("id")
        lines.append(f"## {sec.get('title', sid)}")
        lines.append(f"*{sec.get('description', '')}*")
        lines.append("")
        
        if sid == "high_level_summary":
            lines.append("This brief summarizes the top recommended variants for experimental follow-up, derived from structural analysis, robustness testing, and independent reviewer consensus.")
            lines.append(f"- **Top Consensus Candidates**: {len(strong_candidates)}")
            lines.append(f"- **Disputed Stable Candidates**: {len(disputed_candidates)}")
        elif sid == "robust_candidates":
            if strong_candidates.empty:
                lines.append("No variants reached strong analytical and human consensus.")
            else:
                for _, row in strong_candidates.head(10).iterrows():
                    lines.append(f"- **{row.get('entity_id', 'Unknown')}**: Validated as stable across analytical playbooks and aligned by human reviewers.")
        elif sid == "disputed_candidates":
            if disputed_candidates.empty:
                lines.append("No disputed items in the analytically stable set.")
            else:
                for _, row in disputed_candidates.head(10).iterrows():
                    lines.append(f"- **{row.get('entity_id', 'Unknown')}**: Stable analytically, but lacks reviewer consensus. Recommended for targeted evidence review.")
        elif sid == "caveats":
            lines.append("Executive briefs are deterministically generated from prior decisions and analytical tests. They do not invent new claims. All recommendations represent exploratory structural hypotheses, not confirmed biological mechanism or binding affinity.")
        
        lines.append("")
        
    brief_path.write_text("\n".join(lines), encoding="utf-8")
    
    return {"executive_brief.md": brief_path, "brief_dir": output_dir}
