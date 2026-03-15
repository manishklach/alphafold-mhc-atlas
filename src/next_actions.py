from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv


def build_next_actions(project_dir: Path) -> Path:
    analysis_dir = project_dir / "analysis"
    summary_df = safe_read_csv(analysis_dir / "summary.csv")
    priority_df = safe_read_csv(analysis_dir / "variant_priority_table.csv")
    uncertainty_df = safe_read_csv(analysis_dir / "priority_uncertainty_table.csv")
    review_queue_df = safe_read_csv(project_dir / "review" / "review_queue.csv")
    shortlist_df = safe_read_csv(project_dir / "review" / "shortlist.csv")

    rows: list[dict[str, object]] = []
    if review_queue_df.empty and not priority_df.empty:
        rows.append(
            {
                "entity_type": "project",
                "entity_id": project_dir.name,
                "action_type": "review_in_meeting",
                "priority_level": "high",
                "rationale": "Prioritization rows exist but no review queue has been initialized.",
                "supporting_artifacts": "analysis/variant_priority_table.csv",
                "owner_role_suggestion": "computational_lead",
                "status": "open",
            }
        )
    for record in uncertainty_df.to_dict(orient="records"):
        if str(record.get("uncertainty_level", "")).lower() in {"high", "insufficient_data"}:
            rows.append(
                {
                    "entity_type": "variant",
                    "entity_id": record.get("variant_id", ""),
                    "action_type": "gather_more_evidence",
                    "priority_level": "high",
                    "rationale": f"Uncertainty level is {record.get('uncertainty_level', 'NA')}.",
                    "supporting_artifacts": "analysis/priority_uncertainty_table.csv",
                    "owner_role_suggestion": "scientist",
                    "status": "open",
                }
            )
    for record in shortlist_df.to_dict(orient="records"):
        rows.append(
            {
                "entity_type": "variant",
                "entity_id": record.get("entity_id", ""),
                "action_type": "review_in_meeting",
                "priority_level": "high",
                "rationale": "Shortlisted item should be reviewed in the next decision meeting.",
                "supporting_artifacts": "review/shortlist.csv",
                "owner_role_suggestion": "manager",
                "status": "open",
            }
        )
    if not shortlist_df.empty and not (project_dir / "handoff_bundles").exists():
        rows.append(
            {
                "entity_type": "project",
                "entity_id": project_dir.name,
                "action_type": "ready_for_handoff",
                "priority_level": "medium",
                "rationale": "Shortlist exists but no handoff bundle has been created.",
                "supporting_artifacts": "review/shortlist.csv",
                "owner_role_suggestion": "computational_lead",
                "status": "open",
            }
        )
    if summary_df.empty:
        rows.append(
            {
                "entity_type": "project",
                "entity_id": project_dir.name,
                "action_type": "gather_more_evidence",
                "priority_level": "high",
                "rationale": "summary.csv is missing; downstream review should be deferred.",
                "supporting_artifacts": "analysis/summary.csv",
                "owner_role_suggestion": "computational_lead",
                "status": "open",
            }
        )
    next_actions_df = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
    output_path = analysis_dir / "next_action_table.csv"
    next_actions_df.to_csv(output_path, index=False)
    return output_path
