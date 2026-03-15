import pandas as pd

from src.config import HypothesisGenerationConfig
from src.hypothesis_generation import build_hypotheses


def test_hypothesis_generation_from_toy_inputs() -> None:
    fingerprint_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "delta_contacts_at_anchor_positions_vs_wt": -2.0,
            },
            {
                "variant_id": "v2",
                "delta_contacts_at_anchor_positions_vs_wt": -1.0,
            },
            {
                "variant_id": "v3",
                "delta_contacts_at_anchor_positions_vs_wt": -0.5,
            },
        ]
    )
    allele_df = pd.DataFrame(
        [
            {"allele_name": "A", "mean_abs_delta_total_contacts_vs_wt": 0.5},
            {"allele_name": "B", "mean_abs_delta_total_contacts_vs_wt": 0.6},
        ]
    )
    pocket_summary_df = pd.DataFrame([{"allele_name": "A", "num_unique_contacting_residues": 4, "contact_density_score": 2.0}])
    region_overlap_df = pd.DataFrame([{"pocket_region": "r1", "allele_count": 1}])
    config = HypothesisGenerationConfig(
        enabled=True,
        min_supporting_variants=3,
        min_supporting_alleles=2,
        include_low_confidence_hypotheses=True,
        require_structural_support=False,
        categories=[
            "shared_tolerance_pattern",
            "anchor_disruption_pattern",
            "allele_specific_contact_network",
            "pocket_region_sensitivity",
        ],
    )
    result = build_hypotheses(
        fingerprint_df,
        allele_df,
        pd.DataFrame([{"num_alleles": 2}]),
        pocket_summary_df,
        region_overlap_df,
        config,
    )
    assert not result.hypotheses_df.empty
    assert "shared_tolerance_pattern" in set(result.hypotheses_df["category"])

