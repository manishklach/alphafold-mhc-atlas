import pytest

from pathlib import Path

from src.input_builder import build_chain_manifest_rows, build_multimer_fasta_text, build_variant_inputs
from src.metrics import build_variant_summary
from src.mutation_generator import generate_single_mutants
from src.sequence_resolver import ResolvedMHCSequences


def _resolved_mhc() -> ResolvedMHCSequences:
    return ResolvedMHCSequences(
        allele_name="HLA-A*02:01",
        class_type="I",
        heavy_chain_sequence="MAVMAPRTLVL",
        beta2m_sequence="MSRSVALAVL",
        source="explicit_config",
        resolved=True,
        metadata_only=False,
        notes=[],
    )


def test_multimer_fasta_generation_and_chain_manifest(tmp_path) -> None:
    variants = generate_single_mutants(
        allele_name="HLA-A*02:01",
        reference_peptide="GILGFVFTL",
        mutation_positions=[2],
        allowed_amino_acids=["A"],
    )
    inputs = build_variant_inputs(
        variants=variants,
        resolved_mhc=_resolved_mhc(),
        fasta_dir=tmp_path,
        write_multimer_fasta=True,
    )

    wt_record = inputs[0]
    fasta_text = Path(wt_record.multimer_fasta_path).read_text(encoding="utf-8")
    assert f">{wt_record.variant.variant_id}|chain=A|role=mhc_heavy_chain" in fasta_text
    assert f">{wt_record.variant.variant_id}|chain=B|role=beta2m" in fasta_text
    assert f">{wt_record.variant.variant_id}|chain=C|role=peptide" in fasta_text

    chain_rows = build_chain_manifest_rows(inputs)
    assert len(chain_rows) == 6
    assert chain_rows[0]["chain_id"] == "A"
    assert chain_rows[0]["sequence_hash"]


def test_build_multimer_fasta_text_is_chain_aware() -> None:
    variants = generate_single_mutants(
        allele_name="HLA-A*02:01",
        reference_peptide="GILGFVFTL",
        mutation_positions=[2],
        allowed_amino_acids=["A"],
    )
    inputs = build_variant_inputs(
        variants=variants,
        resolved_mhc=_resolved_mhc(),
        fasta_dir=Path("."),
        write_multimer_fasta=False,
    )
    text = build_multimer_fasta_text("WT", inputs[0].chain_records)
    assert text.count(">") == 3


def test_wt_relative_deltas_are_computed() -> None:
    records = [
        {
            "variant_id": "WT",
            "prediction_present": True,
            "ranking_confidence": 0.80,
            "mean_plddt": 82.0,
            "pae_mean": 4.0,
            "best_available_confidence": 0.80,
            "best_available_confidence_source": "ranking_confidence",
            "mutated_position": None,
            "mut_residue": None,
        },
        {
            "variant_id": "pos2_ItoA",
            "prediction_present": True,
            "ranking_confidence": 0.75,
            "mean_plddt": 78.0,
            "pae_mean": 5.5,
            "best_available_confidence": 0.75,
            "best_available_confidence_source": "ranking_confidence",
            "mutated_position": 2,
            "mut_residue": "A",
        },
    ]

    summary = build_variant_summary(records, baseline_variant_id="WT")
    mutant = summary[summary["variant_id"] == "pos2_ItoA"].iloc[0]
    assert mutant["delta_confidence_vs_wt"] == pytest.approx(-0.05)
    assert mutant["delta_mean_plddt_vs_wt"] == pytest.approx(-4.0)
    assert mutant["delta_pae_vs_wt"] == pytest.approx(1.5)
