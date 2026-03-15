from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json, safe_read_text


CORE_TABLES = {
    "summary": "analysis/summary.csv",
    "priority": "analysis/variant_priority_table.csv",
    "priority_evidence": "analysis/priority_evidence_table.csv",
    "priority_uncertainty": "analysis/priority_uncertainty_table.csv",
    "panel": "analysis/optimized_mutation_panel.csv",
    "panel_coverage": "analysis/panel_coverage_summary.csv",
    "cross_allele_summary": "analysis/cross_allele_summary.csv",
    "allele_tolerance": "analysis/allele_tolerance_fingerprint.csv",
    "pocket_signature": "analysis/pocket_signature_residues.csv",
    "hypotheses": "analysis/hypotheses.csv",
    "ranking_stability": "analysis/ranking_stability.csv",
    "benchmark_summary": "analysis/benchmark_summary.csv",
    "review_queue": "review/review_queue.csv",
    "shortlist": "review/shortlist.csv",
    "feedback": "review/feedback_log.csv",
    "annotations": "review/annotations.csv",
}


def build_project_inventory(project_dir: Path) -> dict[str, object]:
    analysis_dir = project_dir / "analysis"
    snapshot = safe_read_json(analysis_dir / "analysis_snapshot.json")
    report_summary = safe_read_json(analysis_dir / "report_summary.json")
    summary_df = safe_read_csv(project_dir / "analysis" / "summary.csv")
    priority_df = safe_read_csv(project_dir / "analysis" / "variant_priority_table.csv")
    panel_df = safe_read_csv(project_dir / "analysis" / "optimized_mutation_panel.csv")
    review_queue_df = safe_read_csv(project_dir / "review" / "review_queue.csv")
    shortlist_df = safe_read_csv(project_dir / "review" / "shortlist.csv")
    feedback_df = safe_read_csv(project_dir / "review" / "feedback_log.csv")
    case_root = project_dir / "case_studies"

    tables = {
        name: {
            "path": str((project_dir / relative_path).resolve()),
            "exists": (project_dir / relative_path).exists(),
        }
        for name, relative_path in CORE_TABLES.items()
    }
    plots = sorted(path.name for path in (project_dir / "plots").glob("*.png")) if (project_dir / "plots").exists() else []
    cases = sorted(path.name for path in case_root.iterdir() if path.is_dir()) if case_root.exists() else []

    inventory = {
        "project_name": project_dir.name,
        "project_dir": str(project_dir.resolve()),
        "snapshot": snapshot,
        "report_summary": report_summary,
        "coverage": _build_coverage(summary_df, priority_df, panel_df, review_queue_df, shortlist_df, feedback_df),
        "tables": tables,
        "plots": plots,
        "case_studies": cases,
        "has_report": (analysis_dir / "report.md").exists(),
        "available_modules": _available_modules(tables, plots, cases),
        "notes": _inventory_notes(summary_df, priority_df),
    }
    return inventory


def write_project_inventory(project_dir: Path) -> Path:
    inventory = build_project_inventory(project_dir)
    output_path = project_dir / "analysis" / "project_inventory.json"
    output_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return output_path


def load_project_tables(project_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: safe_read_csv(project_dir / relative_path) for name, relative_path in CORE_TABLES.items()}


def load_project_report(project_dir: Path) -> str:
    return safe_read_text(project_dir / "analysis" / "report.md")


def _build_coverage(
    summary_df: pd.DataFrame,
    priority_df: pd.DataFrame,
    panel_df: pd.DataFrame,
    review_queue_df: pd.DataFrame,
    shortlist_df: pd.DataFrame,
    feedback_df: pd.DataFrame,
) -> dict[str, int]:
    num_variants = int(summary_df["variant_id"].nunique()) if not summary_df.empty and "variant_id" in summary_df.columns else 0
    num_alleles = int(summary_df["allele_name"].nunique()) if not summary_df.empty and "allele_name" in summary_df.columns else 0
    prediction_coverage = (
        int(summary_df["prediction_present"].fillna(False).astype(bool).sum())
        if not summary_df.empty and "prediction_present" in summary_df.columns
        else 0
    )
    structural_coverage = (
        int(summary_df["total_peptide_mhc_contacts"].notna().sum())
        if not summary_df.empty and "total_peptide_mhc_contacts" in summary_df.columns
        else 0
    )
    return {
        "num_variants": num_variants,
        "num_alleles": num_alleles,
        "prediction_coverage": prediction_coverage,
        "structural_coverage": structural_coverage,
        "prioritization_rows": int(len(priority_df)),
        "panel_rows": int(len(panel_df)),
        "review_queue_rows": int(len(review_queue_df)),
        "shortlist_rows": int(len(shortlist_df)),
        "feedback_rows": int(len(feedback_df)),
    }


def _available_modules(tables: dict[str, dict[str, object]], plots: list[str], cases: list[str]) -> list[str]:
    modules = ["overview"]
    if tables["priority"]["exists"]:
        modules.append("prioritization")
    if tables["panel"]["exists"]:
        modules.append("panel_design")
    if tables["review_queue"]["exists"] or tables["feedback"]["exists"]:
        modules.append("pilot_review")
    if tables["cross_allele_summary"]["exists"] or tables["allele_tolerance"]["exists"]:
        modules.append("cross_allele")
    if tables["hypotheses"]["exists"]:
        modules.append("hypotheses")
    if cases:
        modules.append("case_studies")
    if plots:
        modules.append("plots")
    return modules


def _inventory_notes(summary_df: pd.DataFrame, priority_df: pd.DataFrame) -> list[str]:
    notes: list[str] = []
    if summary_df.empty:
        notes.append("No summary table was found.")
    if not summary_df.empty and "structure_path" in summary_df.columns and summary_df["structure_path"].isna().all():
        notes.append("No structure paths were available in summary.csv.")
    if priority_df.empty:
        notes.append("No prioritization table was found.")
    return notes
