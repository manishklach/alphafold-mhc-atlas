from __future__ import annotations

import pandas as pd

from .config import PocketSignatureConfig


def build_pocket_signature_residues(
    heavy_chain_contact_df: pd.DataFrame,
    peptide_position_df: pd.DataFrame,
    pocket_config: PocketSignatureConfig,
) -> pd.DataFrame:
    if heavy_chain_contact_df.empty:
        return pd.DataFrame()

    allele_variant_counts = heavy_chain_contact_df.groupby("allele_name", dropna=True)["variant_id"].nunique()
    min_distance_map = _mean_min_distance_per_mhc_residue(heavy_chain_contact_df, peptide_position_df)

    grouped = (
        heavy_chain_contact_df.groupby(["allele_name", "mhc_residue_identifier", "mhc_residue_name"], dropna=True)
        .agg(
            num_variants_contacted=("variant_id", "nunique"),
            peptide_positions_contacted=("peptide_positions_contacted", _merge_position_strings),
        )
        .reset_index()
    )
    grouped["contact_frequency"] = grouped.apply(
        lambda row: row["num_variants_contacted"] / max(1, int(allele_variant_counts.get(row["allele_name"], 1))),
        axis=1,
    )
    grouped["anchor_contact_frequency"] = grouped.apply(
        lambda row: _anchor_frequency(
            heavy_chain_contact_df,
            row["allele_name"],
            row["mhc_residue_identifier"],
            pocket_config.anchor_positions,
        ),
        axis=1,
    )
    grouped["mean_min_distance_to_peptide"] = grouped.apply(
        lambda row: min_distance_map.get((row["allele_name"], row["mhc_residue_identifier"]), pd.NA),
        axis=1,
    )
    grouped["signature_status"] = grouped["num_variants_contacted"].apply(
        lambda value: "ok" if int(value) >= pocket_config.min_contact_frequency else "sparse"
    )
    grouped["signature_notes"] = (
        "Raw residue-identifier comparisons only; no canonical cross-allele numbering is assumed."
    )
    return grouped


def build_pocket_signature_summary(
    pocket_signature_residues_df: pd.DataFrame,
    pocket_config: PocketSignatureConfig,
) -> pd.DataFrame:
    if pocket_signature_residues_df.empty:
        return pd.DataFrame()

    grouped = (
        pocket_signature_residues_df.groupby("allele_name", dropna=True)
        .agg(
            num_unique_contacting_residues=("mhc_residue_identifier", "nunique"),
            most_frequent_contacting_residues_serialized=(
                "mhc_residue_identifier",
                lambda values: ";".join(sorted(set(values))[:10]),
            ),
            contact_density_score=("contact_frequency", "sum"),
            anchor_focus_score=("anchor_contact_frequency", "sum"),
        )
        .reset_index()
    )
    grouped["signature_status"] = "ok"
    grouped["signature_notes"] = (
        "Contact density and anchor focus are transparent aggregate summaries over predicted contact patterns."
    )
    return grouped


def _merge_position_strings(values: pd.Series) -> str:
    positions: set[str] = set()
    for value in values.dropna():
        positions.update(str(value).split(";"))
    numeric = sorted(int(position) for position in positions if position)
    return ";".join(str(position) for position in numeric)


def _anchor_frequency(
    heavy_chain_contact_df: pd.DataFrame,
    allele_name: str,
    residue_identifier: str,
    anchor_positions: list[int],
) -> float:
    if not anchor_positions:
        return 0.0
    subset = heavy_chain_contact_df[
        (heavy_chain_contact_df["allele_name"] == allele_name)
        & (heavy_chain_contact_df["mhc_residue_identifier"] == residue_identifier)
    ]
    if subset.empty:
        return 0.0
    anchor_hits = 0
    for positions in subset["peptide_positions_contacted"].fillna(""):
        contacted = {int(value) for value in str(positions).split(";") if value}
        if contacted & set(anchor_positions):
            anchor_hits += 1
    return anchor_hits / len(subset)


def _mean_min_distance_per_mhc_residue(
    heavy_chain_contact_df: pd.DataFrame,
    peptide_position_df: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    if heavy_chain_contact_df.empty or peptide_position_df.empty:
        return {}
    position_lookup = peptide_position_df.set_index(["variant_id", "peptide_position"])["min_distance_to_mhc"].to_dict()
    distances: dict[tuple[str, str], list[float]] = {}
    for row in heavy_chain_contact_df.to_dict(orient="records"):
        positions = [int(value) for value in str(row.get("peptide_positions_contacted", "")).split(";") if value]
        for position in positions:
            distance = position_lookup.get((row["variant_id"], position))
            if pd.isna(distance):
                continue
            key = (row["allele_name"], row["mhc_residue_identifier"])
            distances.setdefault(key, []).append(float(distance))
    return {key: float(sum(values) / len(values)) for key, values in distances.items() if values}
