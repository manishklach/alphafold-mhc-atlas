import textwrap

import pytest

from src.config import load_config
from src.mutation_generator import generate_single_mutants
from src.sequence_resolver import resolve_mhc_sequences


HEAVY = "MAVMAPRTLVLLLSGALALTQTWAGSHSMRYFYTAMSRPGRGEPRFIAVGYVDDTQFVRFDSDAASQRM"
BETA2M = "MSRSVALAVLALLSLSGLEAIQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERI"


def test_load_config_supports_phase2_schema(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            project_name: test_project
            output_dir: outputs/run
            mhc:
              allele_name: HLA-A*02:01
              class_type: I
              heavy_chain_sequence: {HEAVY}
              beta2m_sequence: {BETA2M}
              allow_metadata_only_fallback: false
            peptide:
              wildtype_sequence: GILGFVFTL
              mutation_positions: [2]
              allowed_substitutions: [A, V]
            """
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.project_name == "test_project"
    assert config.alleles[0].allele_name == "HLA-A*02:01"
    assert config.peptides.wildtype_sequences == ["GILGFVFTL"]


def test_load_config_supports_phase1_compatibility(tmp_path) -> None:
    config_path = tmp_path / "legacy.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            allele_name: HLA-A*02:01
            reference_peptide: GILGFVFTL
            mutation_positions: [2]
            allowed_amino_acids: [A, V]
            output_dir: outputs/legacy
            """
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.alleles[0].allele_name == "HLA-A*02:01"
    assert config.peptides.allowed_substitutions == ["A", "V"]
    assert config.alleles[0].allow_metadata_only_fallback is True


def test_explicit_sequence_resolution_wins(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            output_dir: outputs/run
            mhc:
              allele_name: HLA-A*02:01
              class_type: I
              heavy_chain_sequence: {HEAVY}
              beta2m_sequence: {BETA2M}
              reference_file: ref.yaml
              allow_metadata_only_fallback: false
            peptide:
              wildtype_sequence: GILGFVFTL
              mutation_positions: [2]
              allowed_substitutions: [A]
            """
        ),
        encoding="utf-8",
    )
    ref_path = tmp_path / "ref.yaml"
    ref_path.write_text("alleles: {}", encoding="utf-8")

    config = load_config(config_path)
    resolved = resolve_mhc_sequences(config.alleles[0])
    assert resolved.resolved is True
    assert resolved.source == "explicit_config"


def test_local_reference_resolution(tmp_path) -> None:
    ref_path = tmp_path / "alleles.yaml"
    ref_path.write_text(
        textwrap.dedent(
            f"""
            alleles:
              "HLA-A*02:01":
                class_type: "I"
                heavy_chain_sequence: "{HEAVY}"
                beta2m_sequence: "{BETA2M}"
            """
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            output_dir: outputs/run
            mhc:
              allele_name: HLA-A*02:01
              class_type: I
              heavy_chain_sequence: null
              beta2m_sequence: null
              reference_file: alleles.yaml
              allow_metadata_only_fallback: false
            peptide:
              wildtype_sequence: GILGFVFTL
              mutation_positions: [2]
              allowed_substitutions: [A]
            """
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    resolved = resolve_mhc_sequences(config.alleles[0])
    assert resolved.resolved is True
    assert resolved.heavy_chain_sequence == HEAVY
    assert resolved.source.startswith("reference_file:")


def test_unresolved_allele_raises_without_fallback(tmp_path) -> None:
    ref_path = tmp_path / "alleles.yaml"
    ref_path.write_text("alleles: {}", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            output_dir: outputs/run
            mhc:
              allele_name: HLA-A*02:01
              class_type: I
              heavy_chain_sequence: null
              beta2m_sequence: null
              reference_file: alleles.yaml
              allow_metadata_only_fallback: false
            peptide:
              wildtype_sequence: GILGFVFTL
              mutation_positions: [2]
              allowed_substitutions: [A]
            """
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    with pytest.raises(ValueError, match="Unable to resolve sequences"):
        resolve_mhc_sequences(config.alleles[0])


def test_malformed_reference_entry_raises(tmp_path) -> None:
    ref_path = tmp_path / "alleles.yaml"
    ref_path.write_text(
        textwrap.dedent(
            f"""
            alleles:
              "HLA-A*02:01":
                class_type: "I"
                heavy_chain_sequence: "{HEAVY}"
            """
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            output_dir: outputs/run
            mhc:
              allele_name: HLA-A*02:01
              class_type: I
              heavy_chain_sequence: null
              beta2m_sequence: null
              reference_file: alleles.yaml
              allow_metadata_only_fallback: false
            peptide:
              wildtype_sequence: GILGFVFTL
              mutation_positions: [2]
              allowed_substitutions: [A]
            """
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    with pytest.raises(ValueError, match="incomplete"):
        resolve_mhc_sequences(config.alleles[0])


def test_load_config_supports_multi_allele_schema(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            output_dir: outputs/run
            alleles:
              - allele_name: HLA-A*02:01
                class_type: I
                heavy_chain_sequence: {HEAVY}
                beta2m_sequence: {BETA2M}
              - allele_name: HLA-B*07:02
                class_type: I
                heavy_chain_sequence: {HEAVY}
                beta2m_sequence: {BETA2M}
            peptides:
              mode: shared_panel
              wildtype_sequences: [GILGFVFTL]
              mutation_positions: [2]
              allowed_substitutions: [A]
            """
        ),
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert len(config.alleles) == 2
    assert config.peptides.mode == "shared_panel"


def test_variant_ids_are_deterministic_across_alleles() -> None:
    variants_a = generate_single_mutants("HLA-A*02:01", "GILGFVFTL", [2], ["A"])
    variants_b = generate_single_mutants("HLA-B*07:02", "GILGFVFTL", [2], ["A"])
    assert variants_a[0].variant_id != variants_b[0].variant_id
    assert variants_a[0].local_variant_id == variants_b[0].local_variant_id == "WT"


def test_load_config_supports_phase5_sections(tmp_path) -> None:
    mapping_path = tmp_path / "pocket_regions.yaml"
    mapping_path.write_text(
        textwrap.dedent(
            """
            class_I:
              region_definitions:
                region_a:
                  residues: ["45"]
            """
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            output_dir: outputs/run
            alleles:
              - allele_name: HLA-A*02:01
                class_type: I
                heavy_chain_sequence: {HEAVY}
                beta2m_sequence: {BETA2M}
            peptides:
              mode: shared_panel
              wildtype_sequences: [GILGFVFTL]
              mutation_positions: [2]
              allowed_substitutions: [A]
            reporting:
              enabled: true
            pocket_regions:
              enabled: true
              mapping_file: pocket_regions.yaml
            case_studies:
              enabled: true
              definitions:
                - case_id: anchor_panel
                  description: Example
                  alleles: [HLA-A*02:01]
                  mutation_positions: [2]
                  substitutions: [A]
            """
        ),
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.reporting.enabled is True
    assert config.pocket_regions.mapping_file == mapping_path.resolve()
    assert config.case_studies_enabled is True
    assert config.case_studies[0].case_id == "anchor_panel"
