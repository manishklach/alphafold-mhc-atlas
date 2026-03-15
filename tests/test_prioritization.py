import pandas as pd

from src.config import PrioritizationConfig, RankingFeatureConfig, RankingModeConfig
from src.prioritization import run_prioritization


def test_run_prioritization_builds_decomposable_scores() -> None:
    feature_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "allele_name": "HLA-A*02:01",
                "mutant_peptide": "GILGFVFTA",
                "mutated_position": 9,
                "wt_residue": "L",
                "mut_residue": "A",
                "delta_total_contacts_vs_wt": -4.0,
                "delta_mean_min_distance_vs_wt": 1.0,
                "anchor_disruption_flag": 1,
            },
            {
                "variant_id": "v2",
                "allele_name": "HLA-A*02:01",
                "mutant_peptide": "GILGFVFAL",
                "mutated_position": 8,
                "wt_residue": "T",
                "mut_residue": "A",
                "delta_total_contacts_vs_wt": -1.0,
                "delta_mean_min_distance_vs_wt": 0.1,
                "anchor_disruption_flag": 0,
            },
        ]
    )
    uncertainty_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "ranking_mode": "disruptive_mutations",
                "evidence_coverage_score": 1.0,
                "uncertainty_level": "low",
            },
            {
                "variant_id": "v2",
                "ranking_mode": "disruptive_mutations",
                "evidence_coverage_score": 1.0,
                "uncertainty_level": "low",
            },
        ]
    )
    config = PrioritizationConfig(
        enabled=True,
        default_top_k=5,
        ranking_modes={
                "disruptive_mutations": RankingModeConfig(
                    enabled=True,
                    normalize_features=False,
                    require_structural_support=False,
                    features=[
                    RankingFeatureConfig("delta_total_contacts_vs_wt", -1.0),
                    RankingFeatureConfig("delta_mean_min_distance_vs_wt", 0.5),
                    RankingFeatureConfig("anchor_disruption_flag", 1.0),
                ],
            )
        },
    )

    result = run_prioritization(feature_df, uncertainty_df, config)

    assert list(result.variant_priority_df["variant_id"]) == ["v1", "v2"]
    assert result.variant_priority_df.iloc[0]["priority_score"] > result.variant_priority_df.iloc[1]["priority_score"]
    assert "delta_total_contacts_vs_wt" in result.variant_priority_df.iloc[0]["evidence_components_serialized"]
    assert set(result.evidence_df["evidence_name"]) == {
        "delta_total_contacts_vs_wt",
        "delta_mean_min_distance_vs_wt",
        "anchor_disruption_flag",
    }


def test_run_prioritization_handles_missing_features_gracefully() -> None:
    feature_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "allele_name": "HLA-A*02:01",
                "mutant_peptide": "AAA",
                "mutated_position": 1,
                "wt_residue": "G",
                "mut_residue": "A",
                "delta_total_contacts_vs_wt": None,
            }
        ]
    )
    uncertainty_df = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "ranking_mode": "disruptive_mutations",
                "evidence_coverage_score": 0.2,
                "uncertainty_level": "high",
            }
        ]
    )
    config = PrioritizationConfig(
        enabled=True,
        default_top_k=5,
        ranking_modes={
                "disruptive_mutations": RankingModeConfig(
                    enabled=True,
                    normalize_features=False,
                    require_structural_support=False,
                    features=[RankingFeatureConfig("delta_total_contacts_vs_wt", -1.0)],
                )
        },
    )

    result = run_prioritization(feature_df, uncertainty_df, config)

    assert result.variant_priority_df.iloc[0]["priority_score"] == 0.0
    assert result.evidence_df.iloc[0]["evidence_status"] == "missing"
