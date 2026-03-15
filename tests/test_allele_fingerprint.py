import pandas as pd

from src.allele_fingerprint import (
    build_allele_position_fingerprint,
    build_allele_substitution_fingerprint,
    build_allele_tolerance_fingerprint,
)


def test_allele_tolerance_fingerprint_aggregates_by_allele() -> None:
    fingerprint_df = pd.DataFrame(
        [
            {
                "variant_id": "a1",
                "allele_name": "HLA-A*02:01",
                "mutated_position": 2,
                "delta_total_contacts_vs_wt": -1.0,
                "delta_mean_min_distance_vs_wt": 0.5,
                "delta_confidence_vs_wt": -0.1,
                "delta_contacts_at_mutated_position_vs_wt": -1.0,
                "gained_contacting_mhc_residues_count_vs_wt": 0,
                "lost_anchor_contacts": True,
                "mutated_position_contact_pattern_change": 1.0,
            },
            {
                "variant_id": "b1",
                "allele_name": "HLA-B*07:02",
                "mutated_position": 2,
                "delta_total_contacts_vs_wt": 0.0,
                "delta_mean_min_distance_vs_wt": 0.0,
                "delta_confidence_vs_wt": -0.02,
                "delta_contacts_at_mutated_position_vs_wt": 0.0,
                "gained_contacting_mhc_residues_count_vs_wt": 1,
                "lost_anchor_contacts": False,
                "mutated_position_contact_pattern_change": 1.0,
            },
        ]
    )
    allele_df = build_allele_tolerance_fingerprint(fingerprint_df)
    assert set(allele_df["allele_name"]) == {"HLA-A*02:01", "HLA-B*07:02"}
    position_df = build_allele_position_fingerprint(fingerprint_df)
    substitution_df = build_allele_substitution_fingerprint(
        fingerprint_df.assign(mut_residue=["A", "V"])
    )
    assert not position_df.empty
    assert not substitution_df.empty
