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
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for case_study in case_studies:
        case_dir = output_dir / case_study.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        filtered_variants = _filter_df(summary_df, case_study)
        filtered_fingerprint = _filter_df(fingerprint_df, case_study)
        filtered_contacts = _filter_df(structural_contacts_df, case_study)
        filtered_cross_allele = _filter_df(cross_allele_summary_df, case_study, allow_missing_columns=True)

        filtered_variants.to_csv(case_dir / "filtered_variants.csv", index=False)
        filtered_fingerprint.to_csv(case_dir / "filtered_fingerprint.csv", index=False)
        filtered_contacts.to_csv(case_dir / "filtered_contacts.csv", index=False)
        filtered_cross_allele.to_csv(case_dir / "filtered_cross_allele_summary.csv", index=False)

        summary = {
            "case_id": case_study.case_id,
            "description": case_study.description,
            "num_variants": len(filtered_variants),
            "num_fingerprint_rows": len(filtered_fingerprint),
            "num_contact_rows": len(filtered_contacts),
            "status": "ok" if not filtered_variants.empty else "sparse",
            "notes": "Case-study outputs filter existing analysis tables and do not rerun structural inference.",
        }
        (case_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (case_dir / "summary.md").write_text(_build_summary_md(summary), encoding="utf-8")
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
            f"- Notes: {summary['notes']}",
        ]
    )
