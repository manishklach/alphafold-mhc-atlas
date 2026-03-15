import pandas as pd

from src.config import PocketSignatureConfig
from src.pocket_signature import build_pocket_signature_residues, build_pocket_signature_summary


def test_pocket_signature_aggregation() -> None:
    heavy_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "allele_name": "HLA-A*02:01",
                "mhc_residue_identifier": "A:ALA:1",
                "mhc_residue_name": "ALA",
                "peptide_positions_contacted": "2;9",
            },
            {
                "variant_id": "v2",
                "allele_name": "HLA-A*02:01",
                "mhc_residue_identifier": "A:ALA:1",
                "mhc_residue_name": "ALA",
                "peptide_positions_contacted": "2",
            },
            {
                "variant_id": "v3",
                "allele_name": "HLA-B*07:02",
                "mhc_residue_identifier": "A:GLY:5",
                "mhc_residue_name": "GLY",
                "peptide_positions_contacted": "9",
            },
        ]
    )
    peptide_df = pd.DataFrame(
        [
            {"variant_id": "v1", "peptide_position": 2, "min_distance_to_mhc": 3.0},
            {"variant_id": "v1", "peptide_position": 9, "min_distance_to_mhc": 4.0},
            {"variant_id": "v2", "peptide_position": 2, "min_distance_to_mhc": 3.5},
            {"variant_id": "v3", "peptide_position": 9, "min_distance_to_mhc": 5.0},
        ]
    )
    config = PocketSignatureConfig(
        enabled=True,
        min_contact_frequency=1,
        anchor_positions=[2, 9],
        compute_anchor_specific_signatures=True,
        require_confident_chain_mapping=True,
    )
    residues_df = build_pocket_signature_residues(heavy_df, peptide_df, config)
    summary_df = build_pocket_signature_summary(residues_df, config)
    assert "contact_frequency" in residues_df.columns
    assert set(summary_df["allele_name"]) == {"HLA-A*02:01", "HLA-B*07:02"}
