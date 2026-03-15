from pathlib import Path

import pandas as pd
import pytest

from src.cluster_analysis import run_clustering
from src.config import ClusteringConfig, StructureAnalysisConfig, load_config
from src.fingerprint import build_tolerance_fingerprint


def test_tolerance_fingerprint_generation() -> None:
    df = pd.DataFrame(
        [
            {
                "variant_id": "WT",
                "allele_name": "HLA-A*02:01",
                "mutant_peptide": "VY",
                "mutated_position": pd.NA,
                "wt_residue": pd.NA,
                "mut_residue": pd.NA,
                "delta_confidence_vs_wt": 0.0,
                "delta_mean_plddt_vs_wt": 0.0,
                "delta_pae_vs_wt": 0.0,
                "delta_total_contacts_vs_wt": 0.0,
                "delta_contacts_at_mutated_position_vs_wt": pd.NA,
                "delta_mean_min_distance_vs_wt": 0.0,
                "delta_contacts_at_anchor_positions_vs_wt": 0.0,
                "gained_contacting_mhc_residues_count_vs_wt": 0,
                "lost_contacting_mhc_residues_count_vs_wt": 0,
                "peptide_centroid_shift_vs_wt": 0.0,
                "mutated_residue_ca_displacement_vs_wt": pd.NA,
                "peptide_backbone_rmsd_vs_wt": 0.0,
            },
            {
                "variant_id": "pos2_YtoA",
                "allele_name": "HLA-A*02:01",
                "mutant_peptide": "VA",
                "mutated_position": 2,
                "wt_residue": "Y",
                "mut_residue": "A",
                "delta_confidence_vs_wt": -0.1,
                "delta_mean_plddt_vs_wt": -2.0,
                "delta_pae_vs_wt": 0.5,
                "delta_total_contacts_vs_wt": -1.0,
                "delta_contacts_at_mutated_position_vs_wt": -1.0,
                "delta_mean_min_distance_vs_wt": 1.0,
                "delta_contacts_at_anchor_positions_vs_wt": -1.0,
                "gained_contacting_mhc_residues_count_vs_wt": 0,
                "lost_contacting_mhc_residues_count_vs_wt": 1,
                "peptide_centroid_shift_vs_wt": 2.0,
                "mutated_residue_ca_displacement_vs_wt": 1.5,
                "peptide_backbone_rmsd_vs_wt": 1.2,
            },
        ]
    )
    structure_config = StructureAnalysisConfig(
        enabled=True,
        contact_distance_angstrom=4.5,
        use_all_atom_contacts=True,
        fallback_to_ca_distance=True,
        compute_wt_deltas=True,
        compute_optional_geometry_metrics=True,
        mutated_positions_of_interest=[],
        anchor_positions=[2],
        require_confident_chain_mapping=True,
    )
    fingerprint = build_tolerance_fingerprint(df, structure_config)
    assert "mutated_position_contact_pattern_change" in fingerprint.columns
    assert "lost_anchor_contacts" in fingerprint.columns


def test_clustering_skips_with_too_few_variants(tmp_path) -> None:
    fingerprint_df = pd.DataFrame(
        [
            {
                "variant_id": "pos2_YtoA",
                "delta_confidence_vs_wt": -0.1,
                "delta_total_contacts_vs_wt": -1.0,
                "delta_mean_min_distance_vs_wt": 1.0,
                "delta_contacts_at_mutated_position_vs_wt": -1.0,
            }
        ]
    )
    config = ClusteringConfig(
        enabled=True,
        min_variants_required=5,
        features=[
            "delta_confidence_vs_wt",
            "delta_total_contacts_vs_wt",
            "delta_mean_min_distance_vs_wt",
            "delta_contacts_at_mutated_position_vs_wt",
        ],
        standardize=True,
    )
    result = run_clustering(fingerprint_df, config, tmp_path)
    assert result.ran is False
    assert "Need at least" in result.notes


def test_phase3_config_validation_rejects_negative_contact_threshold(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
output_dir: outputs/run
mhc:
  allele_name: HLA-A*02:01
  class_type: I
  heavy_chain_sequence: ACDEFGHIKL
  beta2m_sequence: MNPQRSTVWY
  allow_metadata_only_fallback: false
peptide:
  wildtype_sequence: GILGFVFTL
  mutation_positions: [2]
  allowed_substitutions: [A]
structure_analysis:
  contact_distance_angstrom: -1
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="contact_distance_angstrom"):
        load_config(config_path)
