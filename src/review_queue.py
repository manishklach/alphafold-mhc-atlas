from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .review_state import ensure_review_dirs


DEFAULT_REVIEW_STATUS = "queued"


def create_review_queue_from_scenario(project_dir: Path, scenario_result: dict[str, object], reviewer: str = "unspecified") -> Path:
    paths = ensure_review_dirs(project_dir)
    ranked = scenario_result.get("ranked_variants", pd.DataFrame())
    if ranked is None or getattr(ranked, "empty", True):
        pd.DataFrame().to_csv(paths.review_queue_csv, index=False)
        return paths.review_queue_csv

    rows = []
    for record in ranked.to_dict(orient="records"):
        rows.append(
            {
                "entity_type": "variant",
                "entity_id": record.get("variant_id", ""),
                "scenario_id": scenario_result["scenario"]["scenario_id"],
                "review_status": DEFAULT_REVIEW_STATUS,
                "review_tags_serialized": "",
                "rationale": "",
                "reviewer": reviewer,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "linked_evidence_bundle": f"scenario_exports/{scenario_result['scenario']['scenario_id']}/evidence_bundle_{record.get('variant_id', '')}.json",
                "uncertainty_level": record.get("uncertainty_flag", ""),
                "next_action": "",
                "ranking_mode": record.get("ranking_mode", ""),
                "priority_score": record.get("priority_score", ""),
                "evidence_coverage_score": record.get("evidence_coverage_score", ""),
                "allele_name": record.get("allele_name", ""),
                "mutant_peptide": record.get("mutant_peptide", ""),
                "mutated_position": record.get("mutated_position", ""),
                "mut_residue": record.get("mut_residue", ""),
            }
        )
    pd.DataFrame(rows).to_csv(paths.review_queue_csv, index=False)
    summarize_review_state(project_dir)
    return paths.review_queue_csv


def update_review_item(
    project_dir: Path,
    entity_id: str,
    review_status: str,
    reviewer: str = "unspecified",
    rationale: str = "",
    next_action: str = "",
    tags: list[str] | None = None,
) -> Path:
    paths = ensure_review_dirs(project_dir)
    df = safe_read_csv(paths.review_queue_csv)
    if df.empty or "entity_id" not in df.columns:
        return paths.review_queue_csv
    mask = df["entity_id"].astype(str) == str(entity_id)
    if not mask.any():
        return paths.review_queue_csv
    for column in ["review_status", "reviewer", "rationale", "next_action", "review_tags_serialized", "timestamp"]:
        if column in df.columns:
            df[column] = df[column].astype(object)
    df.loc[mask, "review_status"] = review_status
    df.loc[mask, "reviewer"] = reviewer
    df.loc[mask, "rationale"] = rationale
    df.loc[mask, "next_action"] = next_action
    df.loc[mask, "review_tags_serialized"] = ";".join(tags or [])
    df.loc[mask, "timestamp"] = datetime.now(timezone.utc).isoformat()
    df.to_csv(paths.review_queue_csv, index=False)
    summarize_review_state(project_dir)
    return paths.review_queue_csv


def summarize_review_state(project_dir: Path) -> None:
    paths = ensure_review_dirs(project_dir)
    queue_df = safe_read_csv(paths.review_queue_csv)
    if queue_df.empty:
        return
    summary = (
        queue_df.groupby("review_status", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    summary.to_csv(paths.review_status_summary_csv, index=False)
    shortlist = queue_df[queue_df["review_status"].isin(["shortlisted", "report_inclusion", "experimental_followup"])].reset_index(drop=True)
    shortlist.to_csv(paths.shortlist_csv, index=False)
    rejected = queue_df[queue_df["review_status"] == "rejected"].reset_index(drop=True)
    rejected.to_csv(paths.rejected_csv, index=False)
