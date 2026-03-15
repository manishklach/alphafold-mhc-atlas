from __future__ import annotations

from typing import Iterable

import pandas as pd


def apply_variant_filters(
    df: pd.DataFrame,
    alleles: Iterable[str] | None = None,
    peptides: Iterable[str] | None = None,
    positions: Iterable[int] | None = None,
    substitutions: Iterable[str] | None = None,
    ranking_mode: str | None = None,
    evidence_coverage_min: float | None = None,
    allowed_uncertainty: Iterable[str] | None = None,
    require_structural_support: bool = False,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filtered = df.copy()
    allele_values = [value for value in (alleles or []) if value]
    peptide_values = [value for value in (peptides or []) if value]
    position_values = [int(value) for value in (positions or [])]
    substitution_values = [str(value) for value in (substitutions or []) if value]
    uncertainty_values = [str(value) for value in (allowed_uncertainty or []) if value]

    if allele_values and "allele_name" in filtered.columns:
        filtered = filtered[filtered["allele_name"].isin(allele_values)]
    if peptide_values:
        peptide_column = "wildtype_peptide" if "wildtype_peptide" in filtered.columns else "mutant_peptide"
        if peptide_column in filtered.columns:
            filtered = filtered[filtered[peptide_column].isin(peptide_values)]
    if position_values and "mutated_position" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["mutated_position"], errors="coerce").isin(position_values)]
    if substitution_values and "mut_residue" in filtered.columns:
        filtered = filtered[filtered["mut_residue"].astype(str).isin(substitution_values)]
    if ranking_mode and "ranking_mode" in filtered.columns:
        filtered = filtered[filtered["ranking_mode"] == ranking_mode]
    if evidence_coverage_min is not None and "evidence_coverage_score" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["evidence_coverage_score"], errors="coerce") >= evidence_coverage_min]
    if uncertainty_values and "uncertainty_flag" in filtered.columns:
        filtered = filtered[filtered["uncertainty_flag"].astype(str).isin(uncertainty_values)]
    if require_structural_support and "structural_support_status" in filtered.columns:
        filtered = filtered[filtered["structural_support_status"].astype(str).str.lower() == "available"]
    return filtered.reset_index(drop=True)


def unique_values(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return []
    values = sorted({str(value) for value in df[column].dropna().tolist() if str(value).strip()})
    return values
