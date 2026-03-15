from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import CaseStudySpec


def run_case_studies(
    case_studies: list[CaseStudySpec],
    output_dir: Path,
    summary_df: pd.DataFrame,
    fingerprint_df: pd.DataFrame,
    structural_contacts_df: pd.DataFrame,
    cross_allele_summary_df: pd.DataFrame,
    priority_df: pd.DataFrame | None = None,
    priority_evidence_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
    robustness_df: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for case_study in case_studies:
        case_dir = output_dir / case_study.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        filtered_variants = _filter_df(summary_df, case_study)
        filtered_fingerprint = _filter_df(fingerprint_df, case_study)
        filtered_contacts = _filter_df(structural_contacts_df, case_study)
        filtered_cross_allele = _filter_df(cross_allele_summary_df, case_study, allow_missing_columns=True)
        filtered_priority = _filter_df(priority_df if priority_df is not None else pd.DataFrame(), case_study)
        filtered_panel = _filter_df(panel_df if panel_df is not None else pd.DataFrame(), case_study)
        filtered_robustness = _filter_rank_stability(
            robustness_df if robustness_df is not None else pd.DataFrame(),
            filtered_priority,
        )
        filtered_priority_evidence = _filter_priority_evidence(
            priority_evidence_df if priority_evidence_df is not None else pd.DataFrame(),
            filtered_priority,
        )

        filtered_variants.to_csv(case_dir / "filtered_variants.csv", index=False)
        filtered_fingerprint.to_csv(case_dir / "filtered_fingerprint.csv", index=False)
        filtered_contacts.to_csv(case_dir / "filtered_contacts.csv", index=False)
        filtered_cross_allele.to_csv(case_dir / "filtered_cross_allele_summary.csv", index=False)
        filtered_priority.to_csv(case_dir / "ranked_variants.csv", index=False)
        filtered_priority_evidence.to_csv(case_dir / "priority_evidence.csv", index=False)
        filtered_panel.to_csv(case_dir / "optimized_panel.csv", index=False)
        filtered_robustness.to_csv(case_dir / "robustness_summary.csv", index=False)

        summary = {
            "case_id": case_study.case_id,
            "description": case_study.description,
            "num_variants": len(filtered_variants),
            "num_fingerprint_rows": len(filtered_fingerprint),
            "num_contact_rows": len(filtered_contacts),
            "num_ranked_rows": len(filtered_priority),
            "num_panel_rows": len(filtered_panel),
            "status": "ok" if not filtered_variants.empty else "sparse",
            "notes": "Case-study outputs filter existing analysis tables and do not rerun structural inference or ranking.",
        }
        (case_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (case_dir / "summary.md").write_text(_build_summary_md(summary), encoding="utf-8")
        (case_dir / "panel_report.md").write_text(_build_panel_report(summary, filtered_panel), encoding="utf-8")
        pd.DataFrame(
            [
                {
                    "table_id": "filtered_variants",
                    "path": str(case_dir / "filtered_variants.csv"),
                    "description": "Allele- and mutation-filtered variant summary rows.",
                },
                {
                    "table_id": "filtered_fingerprint",
                    "path": str(case_dir / "filtered_fingerprint.csv"),
                    "description": "Filtered variant-level tolerance fingerprint rows.",
                },
                {
                    "table_id": "ranked_variants",
                    "path": str(case_dir / "ranked_variants.csv"),
                    "description": "Case-study filtered prioritization rows.",
                },
                {
                    "table_id": "optimized_panel",
                    "path": str(case_dir / "optimized_panel.csv"),
                    "description": "Case-study filtered compact panel selections.",
                },
            ]
        ).to_csv(case_dir / "tables_manifest.csv", index=False)
        pd.DataFrame(
            [
                {
                    "figure_id": "case_study_placeholder",
                    "path": "",
                    "description": "No case-specific plots were selected from the current outputs.",
                    "status": "skipped",
                }
            ]
        ).to_csv(case_dir / "figures_manifest.csv", index=False)
        results.append(summary)
    return results


def _filter_df(df: pd.DataFrame, case_study: CaseStudySpec, allow_missing_columns: bool = False) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filtered = df.copy()
    if case_study.alleles and "allele_name" in filtered.columns:
        filtered = filtered[filtered["allele_name"].isin(case_study.alleles)]
    elif case_study.alleles and not allow_missing_columns:
        return filtered.iloc[0:0]
    if case_study.peptides and "wildtype_peptide" in filtered.columns:
        filtered = filtered[filtered["wildtype_peptide"].isin(case_study.peptides)]
    if case_study.peptides and "mutant_peptide" in filtered.columns and "wildtype_peptide" not in filtered.columns:
        filtered = filtered[filtered["mutant_peptide"].isin(case_study.peptides)]
    if case_study.mutation_positions and "mutated_position" in filtered.columns:
        positions = pd.to_numeric(filtered["mutated_position"], errors="coerce")
        filtered = filtered[positions.isin(case_study.mutation_positions)]
    if case_study.substitutions and "mut_residue" in filtered.columns:
        filtered = filtered[filtered["mut_residue"].isin(case_study.substitutions)]
    if case_study.variants and "variant_id" in filtered.columns:
        filtered = filtered[filtered["variant_id"].isin(case_study.variants)]
    return filtered


def _build_summary_md(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# Case Study: {summary['case_id']}",
            "",
            str(summary["description"]),
            "",
            f"- Status: {summary['status']}",
            f"- Filtered variants: {summary['num_variants']}",
            f"- Filtered fingerprint rows: {summary['num_fingerprint_rows']}",
            f"- Filtered contact rows: {summary['num_contact_rows']}",
            f"- Ranked rows: {summary['num_ranked_rows']}",
            f"- Panel rows: {summary['num_panel_rows']}",
            f"- Notes: {summary['notes']}",
        ]
    )


def _build_panel_report(summary: dict[str, object], panel_df: pd.DataFrame) -> str:
    lines = [
        f"# Panel Report: {summary['case_id']}",
        "",
        f"- Status: {summary['status']}",
        f"- Selected rows: {summary['num_panel_rows']}",
        "",
    ]
    if panel_df.empty:
        lines.append("No case-study-specific panel rows were available.")
    else:
        for row in panel_df.head(10).to_dict(orient="records"):
            lines.append(
                f"- `{row.get('panel_id', 'panel')}` includes `{row.get('variant_id', 'NA')}` "
                f"because {row.get('selection_reason', 'no explicit reason was recorded')}."
            )
    return "\n".join(lines)


def _filter_priority_evidence(evidence_df: pd.DataFrame, priority_df: pd.DataFrame) -> pd.DataFrame:
    if evidence_df.empty or priority_df.empty or "variant_id" not in evidence_df.columns:
        return evidence_df.copy()
    return evidence_df[evidence_df["variant_id"].isin(priority_df["variant_id"])]


def _filter_rank_stability(robustness_df: pd.DataFrame, priority_df: pd.DataFrame) -> pd.DataFrame:
    if robustness_df.empty or priority_df.empty or "variant_id" not in robustness_df.columns:
        return robustness_df.copy()
    return robustness_df[robustness_df["variant_id"].isin(priority_df["variant_id"])]
