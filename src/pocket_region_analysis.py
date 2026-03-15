from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .config import PocketRegionsConfig


def load_pocket_region_mapping(mapping_file: Path | None) -> dict[str, Any]:
    if mapping_file is None or not mapping_file.exists():
        return {}
    suffix = mapping_file.suffix.lower()
    text = mapping_file.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"Unsupported pocket-region mapping extension: {mapping_file.suffix}")
    if not isinstance(data, dict):
        raise ValueError("Pocket-region mapping must deserialize to an object.")
    return data


def build_pocket_region_outputs(
    heavy_chain_contact_df: pd.DataFrame,
    config: PocketRegionsConfig,
    class_type: str = "I",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mapping = load_pocket_region_mapping(config.mapping_file) if config.enabled or config.mapping_file else {}
    class_mapping = mapping.get(f"class_{class_type}", {}) if mapping else {}
    region_definitions = class_mapping.get("region_definitions", {}) if isinstance(class_mapping, dict) else {}

    if not region_definitions:
        if config.require_region_mapping_for_comparison:
            raise ValueError("Pocket-region comparison requested but no region definitions were available.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    residue_to_region = _build_residue_to_region_map(region_definitions)
    if heavy_chain_contact_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    annotated = heavy_chain_contact_df.copy()
    annotated["pocket_region"] = annotated["mhc_residue_identifier"].map(residue_to_region)
    annotated = annotated.dropna(subset=["pocket_region"])
    if annotated.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    region_contacts = (
        annotated.groupby(["allele_name", "variant_id", "pocket_region"], dropna=True)
        .agg(
            contacted_residues=("mhc_residue_identifier", lambda values: ";".join(sorted(set(values)))),
            num_contact_residues=("mhc_residue_identifier", "nunique"),
            peptide_positions_contacted=("peptide_positions_contacted", _merge_serialized_positions),
        )
        .reset_index()
    )
    region_contacts["comparison_mode"] = "user_defined_raw_identifier_mapping"

    allele_region_signature = (
        annotated.groupby(["allele_name", "pocket_region"], dropna=True)
        .agg(
            num_variants_with_region_contacts=("variant_id", "nunique"),
            num_unique_region_residues=("mhc_residue_identifier", "nunique"),
            region_contact_frequency=("variant_id", "count"),
            contacted_residues=("mhc_residue_identifier", lambda values: ";".join(sorted(set(values)))),
        )
        .reset_index()
    )
    allele_counts = annotated.groupby("allele_name", dropna=True)["variant_id"].nunique().to_dict()
    allele_region_signature["normalized_region_contact_frequency"] = allele_region_signature.apply(
        lambda row: row["num_variants_with_region_contacts"] / max(1, int(allele_counts.get(row["allele_name"], 1))),
        axis=1,
    )
    allele_region_signature["signature_notes"] = (
        "Region assignments reflect user-supplied raw residue identifiers and are only as comparable as that mapping."
    )

    overlap_summary = (
        allele_region_signature.groupby("pocket_region", dropna=True)
        .agg(
            allele_count=("allele_name", "nunique"),
            alleles=("allele_name", lambda values: ";".join(sorted(set(values)))),
        )
        .reset_index()
    )
    overlap_summary["comparison_notes"] = (
        "Cross-allele overlap is based on shared user-defined region labels, not inferred canonical numbering."
    )
    return region_contacts, allele_region_signature, overlap_summary


def _build_residue_to_region_map(region_definitions: dict[str, Any]) -> dict[str, str]:
    residue_to_region: dict[str, str] = {}
    for region_name, definition in region_definitions.items():
        if not isinstance(definition, dict):
            continue
        for residue in definition.get("residues", []):
            residue_to_region[str(residue).strip()] = str(region_name)
    return residue_to_region


def _merge_serialized_positions(values: pd.Series) -> str:
    positions: set[int] = set()
    for value in values.dropna():
        positions.update(int(item) for item in str(value).split(";") if item)
    return ";".join(str(position) for position in sorted(positions))
