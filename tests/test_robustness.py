import pandas as pd

from src.config import (
    PrioritizationConfig,
    RankingFeatureConfig,
    RankingModeConfig,
    RobustnessConfig,
)
from src.prioritization import run_prioritization
from src.robustness import run_robustness_analysis


def test_robustness_reports_rank_shifts() -> None:
    feature_df = pd.DataFrame(
        [
            {"variant_id": "v1", "allele_name": "A", "mutant_peptide": "P1", "mutated_position": 1, "wt_residue": "G", "mut_residue": "A", "delta_total_contacts_vs_wt": -4.0},
            {"variant_id": "v2", "allele_name": "A", "mutant_peptide": "P2", "mutated_position": 2, "wt_residue": "I", "mut_residue": "A", "delta_total_contacts_vs_wt": -2.0},
        ]
    )
    uncertainty_df = pd.DataFrame(
        [
            {"variant_id": "v1", "ranking_mode": "disruptive_mutations", "evidence_coverage_score": 1.0, "uncertainty_level": "low"},
            {"variant_id": "v2", "ranking_mode": "disruptive_mutations", "evidence_coverage_score": 1.0, "uncertainty_level": "low"},
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
    baseline = run_prioritization(feature_df, uncertainty_df, config)

    result = run_robustness_analysis(
        feature_df,
        uncertainty_df,
        baseline.variant_priority_df,
        config,
        RobustnessConfig(
            enabled=True,
            contact_distance_thresholds=[4.0, 4.5],
            weight_perturbation_fraction=0.5,
            missing_feature_drop_tests=True,
            replicate_consistency=True,
            compare_top_k=[1],
        ),
    )

    assert not result.robustness_summary_df.empty
    assert not result.ranking_stability_df.empty
    assert "Fragile" in result.report_markdown or "Stable" in result.report_markdown
