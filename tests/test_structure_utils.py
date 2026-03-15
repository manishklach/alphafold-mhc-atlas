from pathlib import Path

from src.input_builder import ChainRecord, VariantInputRecord
from src.mutation_generator import VariantRecord
from src.structure_utils import load_structure, map_chain_roles


def _variant_input(peptide_sequence: str = "VY") -> VariantInputRecord:
    variant = VariantRecord(
        variant_id="HLA_A_02_01__pep_VY__WT",
        local_variant_id="WT",
        peptide_id="pep_VY",
        allele_name="HLA-A*02:01",
        wildtype_peptide=peptide_sequence,
        mutant_peptide=peptide_sequence,
        mutated_position=None,
        wt_residue=None,
        mut_residue=None,
        is_wildtype=True,
    )
    return VariantInputRecord(
        variant=variant,
        chain_records=[
            ChainRecord(variant.variant_id, "A", "mhc_heavy_chain", "AG", None),
            ChainRecord(variant.variant_id, "B", "beta2m", "S", None),
            ChainRecord(variant.variant_id, "C", "peptide", peptide_sequence, None),
        ],
        multimer_fasta_path=None,
        colabfold_query=None,
        resolution_source="explicit",
        resolution_notes=None,
        metadata_only=False,
    )


def test_load_structure_reads_toy_pdb() -> None:
    path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    structure = load_structure(path)
    assert structure is not None
    assert structure.structure_format == "pdb"
    assert len(structure.chains) == 3
    assert {chain.chain_id for chain in structure.chains} == {"X", "Y", "Z"}


def test_chain_role_mapping_from_expected_sequences() -> None:
    path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    structure = load_structure(path)
    chain_map = map_chain_roles("WT", structure, _variant_input(), require_confident_mapping=True)
    assert chain_map.heavy_chain_chain_id == "X"
    assert chain_map.beta2m_chain_id == "Y"
    assert chain_map.peptide_chain_id == "Z"
    assert chain_map.chain_mapping_confidence in {"high", "medium"}


def test_ambiguous_chain_mapping_is_reported() -> None:
    path = Path(__file__).parent / "fixtures" / "toy_complex.pdb"
    structure = load_structure(path)
    ambiguous = _variant_input(peptide_sequence="AA")
    chain_map = map_chain_roles("WT", structure, ambiguous, require_confident_mapping=True)
    assert chain_map.chain_mapping_confidence in {"unresolved", "low"}
