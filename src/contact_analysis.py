from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import numpy as np

from .config import StructureAnalysisConfig
from .structure_utils import (
    ChainRoleMap,
    ParsedChain,
    ParsedStructure,
    backbone_rmsd,
    get_chain_by_role,
    peptide_centroid,
    residue_distance,
)


@dataclass(frozen=True)
class StructuralAnalysisResult:
    chain_map_row: dict[str, object]
    structural_contacts_row: dict[str, object]
    peptide_position_rows: list[dict[str, object]]
    heavy_chain_rows: list[dict[str, object]]
    structural_deltas_row: dict[str, object]


def analyze_variant_structure(
    variant_record: dict[str, object],
    parsed_structure: ParsedStructure | None,
    chain_map: ChainRoleMap,
    structure_config: StructureAnalysisConfig,
    baseline_result: StructuralAnalysisResult | None = None,
) -> StructuralAnalysisResult:
    chain_map_row = chain_map.to_row()
    default_result = _empty_result(
        variant_record=variant_record,
        structure_path=variant_record.get("structure_path"),
        chain_map=chain_map,
        reason=chain_map.chain_mapping_notes or "Structure analysis unavailable.",
    )

    if not structure_config.enabled:
        return default_result
    if not parsed_structure:
        return default_result
    if structure_config.require_confident_chain_mapping and chain_map.chain_mapping_confidence not in {"high", "medium"}:
        return default_result

    heavy_chain = get_chain_by_role(parsed_structure, chain_map, "mhc_heavy_chain")
    peptide_chain = get_chain_by_role(parsed_structure, chain_map, "peptide")
    if not heavy_chain or not peptide_chain:
        return default_result

    contact_rows, heavy_rows, summary = _extract_contacts(
        variant_record=variant_record,
        structure_path=str(parsed_structure.structure_path),
        peptide_chain=peptide_chain,
        heavy_chain=heavy_chain,
        chain_map=chain_map,
        structure_config=structure_config,
    )

    delta_row = _compute_structural_deltas(
        variant_record=variant_record,
        summary_row=summary,
        peptide_rows=contact_rows,
        parsed_structure=parsed_structure,
        peptide_chain=peptide_chain,
        baseline_result=baseline_result,
        structure_config=structure_config,
    )

    return StructuralAnalysisResult(
        chain_map_row=chain_map_row,
        structural_contacts_row=summary,
        peptide_position_rows=contact_rows,
        heavy_chain_rows=heavy_rows,
        structural_deltas_row=delta_row,
    )


def merge_structural_results(
    parsed_records: list[dict[str, object]],
    structural_results: list[StructuralAnalysisResult],
) -> list[dict[str, object]]:
    result_map = {
        str(result.structural_contacts_row["variant_id"]): {**result.structural_contacts_row, **result.structural_deltas_row}
        for result in structural_results
    }
    merged: list[dict[str, object]] = []
    for record in parsed_records:
        enriched = dict(record)
        structural = result_map.get(str(record["variant_id"]), {})
        enriched.update(structural)
        merged.append(enriched)
    return merged


def _extract_contacts(
    variant_record: dict[str, object],
    structure_path: str,
    peptide_chain: ParsedChain,
    heavy_chain: ParsedChain,
    chain_map: ChainRoleMap,
    structure_config: StructureAnalysisConfig,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    peptide_rows: list[dict[str, object]] = []
    heavy_contact_map: dict[str, dict[str, object]] = {}
    min_distances: list[float] = []

    for residue in peptide_chain.residues:
        contacting_residues: list[str] = []
        contact_count = 0
        min_distance = None
        for heavy_residue in heavy_chain.residues:
            distance = residue_distance(
                residue,
                heavy_residue,
                use_all_atom_contacts=structure_config.use_all_atom_contacts,
                fallback_to_ca_distance=structure_config.fallback_to_ca_distance,
            )
            if distance is None:
                continue
            if min_distance is None or distance < min_distance:
                min_distance = distance
            if distance <= structure_config.contact_distance_angstrom:
                contact_count += 1
                identifier = heavy_residue.residue_identifier
                contacting_residues.append(identifier)
                if identifier not in heavy_contact_map:
                    heavy_contact_map[identifier] = {
                        "variant_id": variant_record["variant_id"],
                        "local_variant_id": variant_record.get("local_variant_id"),
                        "peptide_id": variant_record.get("peptide_id"),
                        "allele_name": variant_record.get("allele_name"),
                        "mhc_residue_identifier": identifier,
                        "mhc_residue_name": heavy_residue.residue_name,
                        "num_peptide_positions_contacted": 0,
                        "peptide_positions_contacted": [],
                    }
                heavy_contact_map[identifier]["num_peptide_positions_contacted"] += 1
                heavy_contact_map[identifier]["peptide_positions_contacted"].append(residue.sequence_index + 1)

        if min_distance is not None:
            min_distances.append(min_distance)
        peptide_rows.append(
            {
                "variant_id": variant_record["variant_id"],
                "local_variant_id": variant_record.get("local_variant_id"),
                "peptide_id": variant_record.get("peptide_id"),
                "allele_name": variant_record.get("allele_name"),
                "peptide_position": residue.sequence_index + 1,
                "peptide_residue": residue.sequence_code,
                "num_mhc_residues_in_contact": contact_count,
                "min_distance_to_mhc": min_distance,
                "contacting_mhc_residue_count": len(contacting_residues),
                "contacting_mhc_residues_serialized": ";".join(contacting_residues),
            }
        )

    heavy_rows = []
    for value in heavy_contact_map.values():
        positions = sorted(set(value["peptide_positions_contacted"]))
        heavy_rows.append(
            {
                "variant_id": value["variant_id"],
                "local_variant_id": value["local_variant_id"],
                "peptide_id": value["peptide_id"],
                "allele_name": value["allele_name"],
                "mhc_residue_identifier": value["mhc_residue_identifier"],
                "mhc_residue_name": value["mhc_residue_name"],
                "num_peptide_positions_contacted": value["num_peptide_positions_contacted"],
                "peptide_positions_contacted": ";".join(str(position) for position in positions),
            }
        )

    summary = {
        "variant_id": variant_record["variant_id"],
        "local_variant_id": variant_record.get("local_variant_id"),
        "peptide_id": variant_record.get("peptide_id"),
        "allele_name": variant_record.get("allele_name"),
        "structure_path": structure_path,
        "peptide_length": peptide_chain.length,
        "total_peptide_mhc_contacts": int(sum(row["num_mhc_residues_in_contact"] for row in peptide_rows)),
        "num_peptide_positions_with_contacts": int(
            sum(1 for row in peptide_rows if int(row["num_mhc_residues_in_contact"]) > 0)
        ),
        "mean_min_distance_to_mhc": float(np.mean(min_distances)) if min_distances else pd.NA,
        "chain_mapping_confidence": chain_map.chain_mapping_confidence,
        "extraction_status": "ok",
        "extraction_notes": chain_map.chain_mapping_notes,
        "_peptide_chain_object": peptide_chain,
    }
    return peptide_rows, heavy_rows, summary


def _compute_structural_deltas(
    variant_record: dict[str, object],
    summary_row: dict[str, object],
    peptide_rows: list[dict[str, object]],
    parsed_structure: ParsedStructure,
    peptide_chain: ParsedChain,
    baseline_result: StructuralAnalysisResult | None,
    structure_config: StructureAnalysisConfig,
) -> dict[str, object]:
    empty = {
        "variant_id": variant_record["variant_id"],
        "local_variant_id": variant_record.get("local_variant_id"),
        "peptide_id": variant_record.get("peptide_id"),
        "allele_name": variant_record.get("allele_name"),
        "delta_total_contacts_vs_wt": pd.NA,
        "delta_mean_min_distance_vs_wt": pd.NA,
        "delta_contacts_at_mutated_position_vs_wt": pd.NA,
        "delta_contacts_at_anchor_positions_vs_wt": pd.NA,
        "gained_contacting_mhc_residues_count_vs_wt": pd.NA,
        "lost_contacting_mhc_residues_count_vs_wt": pd.NA,
        "peptide_centroid_shift_vs_wt": pd.NA,
        "mutated_residue_ca_displacement_vs_wt": pd.NA,
        "peptide_backbone_rmsd_vs_wt": pd.NA,
        "structural_delta_status": "not_available",
        "structural_delta_notes": "WT baseline structure unavailable.",
    }
    if not structure_config.compute_wt_deltas:
        empty["structural_delta_notes"] = "WT-relative structural deltas disabled."
        return empty
    if baseline_result is None:
        return empty

    baseline_summary = baseline_result.structural_contacts_row
    delta_row = dict(empty)
    delta_row["structural_delta_status"] = "ok"
    delta_row["structural_delta_notes"] = None
    delta_row["delta_total_contacts_vs_wt"] = _safe_delta(
        summary_row.get("total_peptide_mhc_contacts"),
        baseline_summary.get("total_peptide_mhc_contacts"),
    )
    delta_row["delta_mean_min_distance_vs_wt"] = _safe_delta(
        summary_row.get("mean_min_distance_to_mhc"),
        baseline_summary.get("mean_min_distance_to_mhc"),
    )

    mutated_position = variant_record.get("mutated_position")
    if mutated_position is not None:
        delta_row["delta_contacts_at_mutated_position_vs_wt"] = _contact_delta_at_position(
            peptide_rows,
            baseline_result.peptide_position_rows,
            int(mutated_position),
        )

    if structure_config.anchor_positions:
        anchor_mutant = sum(
            _contact_count_at_position(peptide_rows, position) for position in structure_config.anchor_positions
        )
        anchor_wt = sum(
            _contact_count_at_position(baseline_result.peptide_position_rows, position)
            for position in structure_config.anchor_positions
        )
        delta_row["delta_contacts_at_anchor_positions_vs_wt"] = anchor_mutant - anchor_wt

    mutant_set = _contacting_residue_set(peptide_rows)
    wt_set = _contacting_residue_set(baseline_result.peptide_position_rows)
    delta_row["gained_contacting_mhc_residues_count_vs_wt"] = len(mutant_set - wt_set)
    delta_row["lost_contacting_mhc_residues_count_vs_wt"] = len(wt_set - mutant_set)

    if structure_config.compute_optional_geometry_metrics:
        delta_row.update(
            _geometry_metrics(
                mutated_position=mutated_position,
                peptide_chain=peptide_chain,
                baseline_result=baseline_result,
                parsed_structure=parsed_structure,
            )
        )

    return delta_row


def _geometry_metrics(
    mutated_position: object,
    peptide_chain: ParsedChain,
    baseline_result: StructuralAnalysisResult,
    parsed_structure: ParsedStructure,
) -> dict[str, object]:
    result = {
        "peptide_centroid_shift_vs_wt": pd.NA,
        "mutated_residue_ca_displacement_vs_wt": pd.NA,
        "peptide_backbone_rmsd_vs_wt": pd.NA,
    }
    baseline_chain = baseline_result.structural_contacts_row.get("_peptide_chain_object")
    if baseline_chain is None:
        return result

    centroid = peptide_centroid(peptide_chain)
    baseline_centroid = peptide_centroid(baseline_chain)
    if centroid is not None and baseline_centroid is not None:
        result["peptide_centroid_shift_vs_wt"] = _euclidean_distance(centroid, baseline_centroid)

    if mutated_position is not None and 1 <= int(mutated_position) <= peptide_chain.length <= baseline_chain.length:
        residue = peptide_chain.residues[int(mutated_position) - 1]
        baseline_residue = baseline_chain.residues[int(mutated_position) - 1]
        if residue.ca_coord is not None and baseline_residue.ca_coord is not None:
            result["mutated_residue_ca_displacement_vs_wt"] = _euclidean_distance(
                residue.ca_coord,
                baseline_residue.ca_coord,
            )

    rmsd = backbone_rmsd(peptide_chain, baseline_chain)
    if rmsd is not None:
        result["peptide_backbone_rmsd_vs_wt"] = rmsd
    return result


def _contact_delta_at_position(
    mutant_rows: list[dict[str, object]],
    wt_rows: list[dict[str, object]],
    position: int,
) -> object:
    mutant_value = _contact_count_at_position(mutant_rows, position)
    wt_value = _contact_count_at_position(wt_rows, position)
    if mutant_value is pd.NA or wt_value is pd.NA:
        return pd.NA
    return mutant_value - wt_value


def _contact_count_at_position(rows: list[dict[str, object]], position: int) -> object:
    for row in rows:
        if int(row["peptide_position"]) == position:
            return int(row["num_mhc_residues_in_contact"])
    return pd.NA


def _contacting_residue_set(rows: list[dict[str, object]]) -> set[str]:
    identifiers: set[str] = set()
    for row in rows:
        serialized = row.get("contacting_mhc_residues_serialized")
        if serialized:
            identifiers.update(str(serialized).split(";"))
    return identifiers


def _safe_delta(value: object, baseline: object) -> object:
    if pd.isna(value) or pd.isna(baseline):
        return pd.NA
    return float(value) - float(baseline)


def _euclidean_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    vec_a = np.asarray(a, dtype=float)
    vec_b = np.asarray(b, dtype=float)
    return float(np.linalg.norm(vec_a - vec_b))


def _empty_result(
    variant_record: dict[str, object],
    structure_path: object,
    chain_map: ChainRoleMap,
    reason: str,
) -> StructuralAnalysisResult:
    summary = {
        "variant_id": variant_record["variant_id"],
        "local_variant_id": variant_record.get("local_variant_id"),
        "peptide_id": variant_record.get("peptide_id"),
        "allele_name": variant_record.get("allele_name"),
        "structure_path": structure_path,
        "peptide_length": pd.NA,
        "total_peptide_mhc_contacts": pd.NA,
        "num_peptide_positions_with_contacts": pd.NA,
        "mean_min_distance_to_mhc": pd.NA,
        "chain_mapping_confidence": chain_map.chain_mapping_confidence,
        "extraction_status": "skipped",
        "extraction_notes": reason,
        "_peptide_chain_object": None,
    }
    deltas = {
        "variant_id": variant_record["variant_id"],
        "local_variant_id": variant_record.get("local_variant_id"),
        "peptide_id": variant_record.get("peptide_id"),
        "allele_name": variant_record.get("allele_name"),
        "delta_total_contacts_vs_wt": pd.NA,
        "delta_mean_min_distance_vs_wt": pd.NA,
        "delta_contacts_at_mutated_position_vs_wt": pd.NA,
        "delta_contacts_at_anchor_positions_vs_wt": pd.NA,
        "gained_contacting_mhc_residues_count_vs_wt": pd.NA,
        "lost_contacting_mhc_residues_count_vs_wt": pd.NA,
        "peptide_centroid_shift_vs_wt": pd.NA,
        "mutated_residue_ca_displacement_vs_wt": pd.NA,
        "peptide_backbone_rmsd_vs_wt": pd.NA,
        "structural_delta_status": "not_available",
        "structural_delta_notes": reason,
    }
    return StructuralAnalysisResult(
        chain_map_row=chain_map.to_row(),
        structural_contacts_row=summary,
        peptide_position_rows=[],
        heavy_chain_rows=[],
        structural_deltas_row=deltas,
    )
