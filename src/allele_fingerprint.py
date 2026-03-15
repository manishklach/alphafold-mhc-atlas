from __future__ import annotations

import pandas as pd


def build_allele_tolerance_fingerprint(fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    if fingerprint_df.empty:
        return pd.DataFrame()
    mutant_df = fingerprint_df[fingerprint_df["mutated_position"].notna()].copy()
    if mutant_df.empty:
        return pd.DataFrame()

    working = mutant_df.copy()
    working["has_contact_loss"] = pd.to_numeric(working["delta_contacts_at_mutated_position_vs_wt"], errors="coerce").lt(0)
    working["has_gained_contacts"] = pd.to_numeric(
        working["gained_contacting_mhc_residues_count_vs_wt"], errors="coerce"
    ).gt(0)
    working["has_anchor_disruption"] = working["lost_anchor_contacts"].fillna(False).astype(bool)
    working["abs_delta_total_contacts_vs_wt"] = pd.to_numeric(
        working["delta_total_contacts_vs_wt"], errors="coerce"
    ).abs()

    grouped = (
        working.groupby("allele_name", dropna=True)
        .agg(
            variant_count=("variant_id", "count"),
            mean_delta_total_contacts_vs_wt=("delta_total_contacts_vs_wt", "mean"),
            mean_abs_delta_total_contacts_vs_wt=("abs_delta_total_contacts_vs_wt", "mean"),
            mean_delta_mean_min_distance_vs_wt=("delta_mean_min_distance_vs_wt", "mean"),
            fraction_with_contact_loss_at_mutated_position=("has_contact_loss", "mean"),
            fraction_with_gained_contacts=("has_gained_contacts", "mean"),
            fraction_with_anchor_disruption=("has_anchor_disruption", "mean"),
            mean_confidence_drop_across_mutants=("delta_confidence_vs_wt", "mean"),
        )
        .reset_index()
    )
    grouped["fingerprint_status"] = "ok"
    grouped["fingerprint_notes"] = None
    return grouped


def build_allele_position_fingerprint(fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_allele_fingerprint(fingerprint_df, ["allele_name", "mutated_position"])


def build_allele_substitution_fingerprint(fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_allele_fingerprint(fingerprint_df, ["allele_name", "mutated_position", "mut_residue"])


def _aggregate_allele_fingerprint(fingerprint_df: pd.DataFrame, group_fields: list[str]) -> pd.DataFrame:
    if fingerprint_df.empty:
        return pd.DataFrame()
    mutant_df = fingerprint_df[fingerprint_df["mutated_position"].notna()].copy()
    if mutant_df.empty:
        return pd.DataFrame()
    grouped = (
        mutant_df.groupby(group_fields, dropna=True)
        .agg(
            variant_count=("variant_id", "count"),
            avg_delta_total_contacts_vs_wt=("delta_total_contacts_vs_wt", "mean"),
            avg_delta_mean_min_distance_vs_wt=("delta_mean_min_distance_vs_wt", "mean"),
            avg_confidence_drop=("delta_confidence_vs_wt", "mean"),
            avg_pattern_change=("mutated_position_contact_pattern_change", "mean"),
        )
        .reset_index()
    )
    return grouped
