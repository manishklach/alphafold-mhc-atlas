from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv


def build_open_questions(project_dir: Path) -> Path:
    uncertainty_df = safe_read_csv(project_dir / "analysis" / "priority_uncertainty_table.csv")
    stability_df = safe_read_csv(project_dir / "analysis" / "ranking_stability.csv")
    feedback_df = safe_read_csv(project_dir / "review" / "feedback_log.csv")
    shortlist_df = safe_read_csv(project_dir / "review" / "shortlist.csv")

    rows: list[dict[str, object]] = []
    for record in uncertainty_df.to_dict(orient="records"):
        level = str(record.get("uncertainty_level", "")).lower()
        if level in {"high", "insufficient_data"}:
            rows.append(
                {
                    "question_id": f"q_{record.get('variant_id', 'unknown')}",
                    "category": "insufficient_evidence",
                    "question_text": f"Should {record.get('variant_id', 'this variant')} be reviewed despite {level} uncertainty?",
                    "linked_entities": str(record.get("variant_id", "")),
                    "linked_artifacts": "analysis/priority_uncertainty_table.csv",
                    "urgency": "high",
                    "notes": record.get("uncertainty_reasons_serialized", ""),
                }
            )
    for record in stability_df.to_dict(orient="records"):
        shift = pd.to_numeric(pd.Series([record.get("rank_shift")]), errors="coerce").iloc[0]
        if pd.notna(shift) and abs(float(shift)) >= 3:
            rows.append(
                {
                    "question_id": f"q_rank_{record.get('variant_id', 'unknown')}",
                    "category": "unstable_ranking",
                    "question_text": f"Why did {record.get('variant_id', 'this variant')} shift rank by {shift} under alternative settings?",
                    "linked_entities": str(record.get("variant_id", "")),
                    "linked_artifacts": "analysis/ranking_stability.csv",
                    "urgency": "medium",
                    "notes": record.get("stability_notes", ""),
                }
            )
    if not feedback_df.empty:
        unresolved = feedback_df[feedback_df.get("status", pd.Series(dtype=object)).astype(str).str.lower() != "resolved"]
        for record in unresolved.head(10).to_dict(orient="records"):
            rows.append(
                {
                    "question_id": f"q_feedback_{record.get('feedback_id', 'unknown')}",
                    "category": "reviewer_comment",
                    "question_text": f"What follow-up is needed for reviewer concern '{record.get('concern_type', 'other')}' on {record.get('entity_id', 'entity')}?",
                    "linked_entities": str(record.get("entity_id", "")),
                    "linked_artifacts": "review/feedback_log.csv",
                    "urgency": "medium",
                    "notes": record.get("free_text_comment", ""),
                }
            )
    if not shortlist_df.empty and "uncertainty_level" in shortlist_df.columns:
        uncertain_rows = shortlist_df[shortlist_df["uncertainty_level"].astype(str).isin(["high", "insufficient_data"])]
        for record in uncertain_rows.to_dict(orient="records"):
            rows.append(
                {
                    "question_id": f"q_shortlist_{record.get('entity_id', 'unknown')}",
                    "category": "shortlist_uncertainty",
                    "question_text": f"Is shortlisted item {record.get('entity_id', 'unknown')} ready for discussion despite elevated uncertainty?",
                    "linked_entities": str(record.get("entity_id", "")),
                    "linked_artifacts": "review/shortlist.csv",
                    "urgency": "high",
                    "notes": record.get("rationale", ""),
                }
            )
    output_dir = project_dir / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    question_df = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
    question_df.to_csv(output_dir / "open_questions.csv", index=False)
    lines = ["# Open Questions", ""]
    if question_df.empty:
        lines.append("- No open questions were generated from the current artifacts.")
    else:
        lines.extend(f"- {row['question_text']}" for row in question_df.to_dict(orient="records"))
    (output_dir / "open_questions.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir / "open_questions.csv"
