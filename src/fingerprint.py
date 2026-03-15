from __future__ import annotations

import pandas as pd

from .config import StructureAnalysisConfig


DEFAULT_FINGERPRINT_FEATURES = [
    "delta_confidence_vs_wt",
    "delta_mean_plddt_vs_wt",
    "delta_pae_vs_wt",
    "delta_total_contacts_vs_wt",
    "delta_contacts_at_mutated_position_vs_wt",
    "delta_mean_min_distance_vs_wt",
    "delta_contacts_at_anchor_positions_vs_wt",
    "gained_contacting_mhc_residues_count_vs_wt",
    "lost_contacting_mhc_residues_count_vs_wt",
    "peptide_centroid_shift_vs_wt",
    "mutated_residue_ca_displacement_vs_wt",
    "peptide_backbone_rmsd_vs_wt",
]


def build_tolerance_fingerprint(
    summary_df: pd.DataFrame,
    structure_config: StructureAnalysisConfig,
) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    df = summary_df.copy()
    for required in ["allele_name", "mutant_peptide", "mutated_position", "wt_residue", "mut_residue"]:
        if required not in df.columns:
            df[required] = pd.NA
    for feature in DEFAULT_FINGERPRINT_FEATURES:
        if feature not in df.columns:
            df[feature] = pd.NA

    df["mutated_position_contact_pattern_change"] = (
        pd.to_numeric(df["gained_contacting_mhc_residues_count_vs_wt"], errors="coerce").fillna(0)
        + pd.to_numeric(df["lost_contacting_mhc_residues_count_vs_wt"], errors="coerce").fillna(0)
    )

    if structure_config.anchor_positions and "delta_contacts_at_anchor_positions_vs_wt" in df.columns:
        anchor_delta = pd.to_numeric(df["delta_contacts_at_anchor_positions_vs_wt"], errors="coerce")
        df["lost_anchor_contacts"] = anchor_delta.lt(0)
        df["gained_anchor_contacts"] = anchor_delta.gt(0)
    else:
        df["lost_anchor_contacts"] = pd.NA
        df["gained_anchor_contacts"] = pd.NA

    df["fingerprint_status"] = df.apply(_fingerprint_status, axis=1)
    df["fingerprint_notes"] = df.apply(_fingerprint_notes, axis=1)

    columns = [
        "variant_id",
        "allele_name",
        "mutant_peptide",
        "mutated_position",
        "wt_residue",
        "mut_residue",
        *DEFAULT_FINGERPRINT_FEATURES,
        "mutated_position_contact_pattern_change",
        "lost_anchor_contacts",
        "gained_anchor_contacts",
        "fingerprint_status",
        "fingerprint_notes",
    ]
    return df[columns]


def aggregate_tolerance_by_position(fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_tolerance(fingerprint_df, ["mutated_position"])


def aggregate_tolerance_by_substitution(fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_tolerance(fingerprint_df, ["mutated_position", "mut_residue"])


def _aggregate_tolerance(fingerprint_df: pd.DataFrame, group_fields: list[str]) -> pd.DataFrame:
    if fingerprint_df.empty:
        return pd.DataFrame()
    available = fingerprint_df[fingerprint_df["mutated_position"].notna()].copy()
    if available.empty:
        return pd.DataFrame()
    grouped = (
        available.groupby(group_fields, dropna=True)
        .agg(
            variant_count=("variant_id", "count"),
            avg_delta_confidence_vs_wt=("delta_confidence_vs_wt", "mean"),
            avg_delta_total_contacts_vs_wt=("delta_total_contacts_vs_wt", "mean"),
            avg_delta_mean_min_distance_vs_wt=("delta_mean_min_distance_vs_wt", "mean"),
            avg_pattern_change=("mutated_position_contact_pattern_change", "mean"),
        )
        .reset_index()
    )
    return grouped


def _fingerprint_status(row: pd.Series) -> str:
    numeric_features = [row.get(feature) for feature in DEFAULT_FINGERPRINT_FEATURES]
    available = sum(0 if pd.isna(value) else 1 for value in numeric_features)
    return "ok" if available >= 2 else "partial"


def _fingerprint_notes(row: pd.Series) -> str | None:
    if row["fingerprint_status"] == "ok":
        return None
    return "Insufficient structural or confidence features were available for a fuller fingerprint."
