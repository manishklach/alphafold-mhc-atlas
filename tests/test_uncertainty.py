import pandas as pd

from src.config import RankingFeatureConfig, RankingModeConfig, UncertaintyConfig
from src.uncertainty import build_priority_uncertainty_table


def test_uncertainty_levels_reflect_support_quality() -> None:
    feature_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "structural_data_present": 1,
                "wt_reference_present": 1,
                "chain_mapping_confident": 1,
                "prediction_complete": 1,
                "delta_total_contacts_vs_wt": -2.0,
            },
            {
                "variant_id": "v2",
                "structural_data_present": 0,
                "wt_reference_present": 0,
                "chain_mapping_confident": 0,
                "prediction_complete": 0,
                "delta_total_contacts_vs_wt": None,
            },
        ]
    )
    ranking_modes = {
        "disruptive_mutations": RankingModeConfig(
            enabled=True,
            normalize_features=False,
            require_structural_support=False,
            features=[RankingFeatureConfig("delta_total_contacts_vs_wt", -1.0)],
        )
    }

    uncertainty_df, coverage_df = build_priority_uncertainty_table(
        feature_df,
        ranking_modes,
        UncertaintyConfig(
            enabled=True,
            penalize_missing_features=True,
            penalize_unconfident_chain_mapping=True,
        ),
    )

    levels = dict(zip(uncertainty_df["variant_id"], uncertainty_df["uncertainty_level"]))
    assert levels["v1"] in {"low", "moderate"}
    assert levels["v2"] == "insufficient_data"
    assert not coverage_df.empty
