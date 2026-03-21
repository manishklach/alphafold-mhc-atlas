import pandas as pd

from core.scoring.prioritization import rank_candidates
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


def test_rank_candidates_scores_comparison_results_transparently() -> None:
    comparison_results_list = [
        {
            "candidate_id": "candidate_high",
            "comparison": {
                "avg_shift": 2.6,
                "max_shift": 3.1,
                "large_shift_count": 4,
                "confidence_delta": -7.0,
                "flags": ["high_structural_change", "confidence_drop"],
            },
        },
        {
            "candidate_id": "candidate_mid",
            "comparison": {
                "avg_shift": 1.4,
                "max_shift": 1.6,
                "large_shift_count": 1,
                "confidence_delta": -2.0,
                "flags": [],
            },
        },
        {
            "candidate_id": "candidate_low",
            "comparison": {
                "avg_shift": 0.2,
                "max_shift": 0.5,
                "large_shift_count": 0,
                "confidence_delta": 0.0,
                "flags": [],
            },
        },
    ]

    ranked = rank_candidates(comparison_results_list)

    assert [item["candidate_id"] for item in ranked] == [
        "candidate_high",
        "candidate_mid",
        "candidate_low",
    ]
    assert ranked[0]["priority_score"] == 7.0
    assert ranked[0]["priority_label"] == "HIGH"
    assert ranked[1]["priority_score"] == 3.0
    assert ranked[1]["priority_label"] == "LOW"
    assert ranked[2]["priority_score"] == 0.0
    assert ranked[2]["priority_label"] == "LOW"
    assert "Significant structural change observed" in ranked[0]["explanation"]
    assert "Confidence decreased, indicating potential instability." in ranked[0]["explanation"]


def test_rank_candidates_softens_confidence_penalty_when_shift_is_low() -> None:
    ranked = rank_candidates(
        [
            {
                "candidate_id": "candidate_uncertain_low_shift",
                "comparison": {
                    "avg_shift": 0.8,
                    "max_shift": 0.9,
                    "large_shift_count": 0,
                    "confidence_delta": -8.0,
                    "flags": ["confidence_drop"],
                },
            }
        ]
    )

    assert ranked[0]["priority_score"] == 0.0
    assert ranked[0]["priority_label"] == "LOW"
