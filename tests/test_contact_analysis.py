from pathlib import Path

import pytest

from src.config import StructureAnalysisConfig
from src.contact_analysis import analyze_variant_structure
from src.input_builder import ChainRecord, VariantInputRecord
from src.mutation_generator import VariantRecord
from src.structure_utils import load_structure, map_chain_roles


def _variant_input(variant_id: str, peptide_sequence: str, mutated_position=None, mut_residue=None) -> VariantInputRecord:
    variant = VariantRecord(
        variant_id=variant_id,
        local_variant_id="WT" if variant_id == "WT" else "pos2_YtoA",
        peptide_id="pep_VY",
        allele_name="HLA-A*02:01",
        wildtype_peptide="VY",
        mutant_peptide=peptide_sequence,
        mutated_position=mutated_position,
        wt_residue="Y" if mutated_position else None,
        mut_residue=mut_residue,
        is_wildtype=variant_id == "WT",
    )
    return VariantInputRecord(
        variant=variant,
        chain_records=[
            ChainRecord(variant_id, "A", "mhc_heavy_chain", "AG", None),
            ChainRecord(variant_id, "B", "beta2m", "S", None),
            ChainRecord(variant_id, "C", "peptide", peptide_sequence, None),
        ],
        multimer_fasta_path=None,
        colabfold_query=None,
        resolution_source="explicit",
        resolution_notes=None,
        metadata_only=False,
    )


def _config() -> StructureAnalysisConfig:
    return StructureAnalysisConfig(
        enabled=True,
        contact_distance_angstrom=4.5,
        use_all_atom_contacts=True,
        fallback_to_ca_distance=True,
        compute_wt_deltas=True,
        compute_optional_geometry_metrics=True,
        mutated_positions_of_interest=[],
        anchor_positions=[1],
        require_confident_chain_mapping=True,
    )


def test_contact_extraction_on_toy_structure() -> None:
    path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    structure = load_structure(path)
    variant_input = _variant_input("WT", "VY")
    chain_map = map_chain_roles("WT", structure, variant_input, require_confident_mapping=True)
    result = analyze_variant_structure(
        variant_record=variant_input.variant.to_dict(),
        parsed_structure=structure,
        chain_map=chain_map,
        structure_config=_config(),
        baseline_result=None,
    )
    summary = result.structural_contacts_row
    assert summary["extraction_status"] == "ok"
    assert summary["total_peptide_mhc_contacts"] >= 1
    assert any(row["peptide_position"] == 1 for row in result.peptide_position_rows)


def test_wt_relative_structural_deltas() -> None:
    wt_path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    mutant_path = Path(__file__).parent / "fixtures" / "toy_complex_mutant.pdb"
    wt_structure = load_structure(wt_path)
    mutant_structure = load_structure(mutant_path)
    wt_input = _variant_input("WT", "VY")
    mutant_input = _variant_input("pos2_YtoA", "VA", mutated_position=2, mut_residue="A")

    wt_map = map_chain_roles("WT", wt_structure, wt_input, require_confident_mapping=True)
    mutant_map = map_chain_roles("pos2_YtoA", mutant_structure, mutant_input, require_confident_mapping=True)

    wt_result = analyze_variant_structure(
        variant_record=wt_input.variant.to_dict(),
        parsed_structure=wt_structure,
        chain_map=wt_map,
        structure_config=_config(),
        baseline_result=None,
    )
    mutant_result = analyze_variant_structure(
        variant_record=mutant_input.variant.to_dict(),
        parsed_structure=mutant_structure,
        chain_map=mutant_map,
        structure_config=_config(),
        baseline_result=wt_result,
    )
    assert mutant_result.structural_deltas_row["delta_total_contacts_vs_wt"] <= 0
    assert mutant_result.structural_deltas_row["delta_contacts_at_anchor_positions_vs_wt"] <= 0


def test_ambiguous_mapping_skips_structural_metrics() -> None:
    path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    structure = load_structure(path)
    ambiguous_input = _variant_input("WT", "AA")
    chain_map = map_chain_roles("WT", structure, ambiguous_input, require_confident_mapping=True)
    result = analyze_variant_structure(
        variant_record=ambiguous_input.variant.to_dict(),
        parsed_structure=structure,
        chain_map=chain_map,
        structure_config=_config(),
        baseline_result=None,
    )
    assert result.structural_contacts_row["extraction_status"] == "skipped"
