import pandas as pd

from src.config import CrossAlleleAnalysisConfig
from src.cross_allele_analysis import build_pocket_jaccard_matrix, run_cross_allele_analysis


def test_pocket_jaccard_matrix() -> None:
    df = pd.DataFrame(
        [
            {"allele_name": "A", "mhc_residue_identifier": "r1"},
            {"allele_name": "A", "mhc_residue_identifier": "r2"},
            {"allele_name": "B", "mhc_residue_identifier": "r2"},
            {"allele_name": "B", "mhc_residue_identifier": "r3"},
        ]
    )
    matrix = build_pocket_jaccard_matrix(df)
    assert matrix.loc["A", "A"] == 1.0
    assert matrix.loc["A", "B"] == matrix.loc["B", "A"]


def test_cross_allele_analysis_runs_with_two_alleles(tmp_path) -> None:
    allele_df = pd.DataFrame(
        [
            {
                "allele_name": "A",
                "mean_delta_total_contacts_vs_wt": -1.0,
                "mean_abs_delta_total_contacts_vs_wt": 1.0,
                "mean_delta_mean_min_distance_vs_wt": 0.5,
                "fraction_with_contact_loss_at_mutated_position": 1.0,
                "fraction_with_gained_contacts": 0.0,
                "fraction_with_anchor_disruption": 1.0,
                "mean_confidence_drop_across_mutants": -0.1,
            },
            {
                "allele_name": "B",
                "mean_delta_total_contacts_vs_wt": 0.0,
                "mean_abs_delta_total_contacts_vs_wt": 0.2,
                "mean_delta_mean_min_distance_vs_wt": 0.1,
                "fraction_with_contact_loss_at_mutated_position": 0.0,
                "fraction_with_gained_contacts": 1.0,
                "fraction_with_anchor_disruption": 0.0,
                "mean_confidence_drop_across_mutants": -0.02,
            },
        ]
    )
    pocket_df = pd.DataFrame(
        [
            {"allele_name": "A", "mhc_residue_identifier": "r1", "contact_frequency": 1.0, "anchor_contact_frequency": 1.0},
            {"allele_name": "A", "mhc_residue_identifier": "r2", "contact_frequency": 0.5, "anchor_contact_frequency": 0.5},
            {"allele_name": "B", "mhc_residue_identifier": "r2", "contact_frequency": 0.5, "anchor_contact_frequency": 0.5},
            {"allele_name": "B", "mhc_residue_identifier": "r3", "contact_frequency": 1.0, "anchor_contact_frequency": 0.0},
        ]
    )
    allele_position_df = pd.DataFrame(
        [
            {"allele_name": "A", "avg_delta_total_contacts_vs_wt": -1.0},
            {"allele_name": "B", "avg_delta_total_contacts_vs_wt": 0.0},
        ]
    )
    config = CrossAlleleAnalysisConfig(
        enabled=True,
        require_min_alleles=2,
        compare_pocket_signatures=True,
        compare_tolerance_fingerprints=True,
        compare_anchor_patterns=True,
        use_combined_similarity=True,
        numeric_metric="euclidean",
        set_based_metric="jaccard",
        standardize_numeric_features=True,
    )
    result = run_cross_allele_analysis(allele_df, pocket_df, allele_position_df, config, tmp_path)
    assert result.ran is True
    assert not result.allele_similarity_matrix.empty


def test_cross_allele_analysis_skips_with_too_few_alleles(tmp_path) -> None:
    allele_df = pd.DataFrame(
        [
            {
                "allele_name": "A",
                "mean_delta_total_contacts_vs_wt": -1.0,
            }
        ]
    )
    config = CrossAlleleAnalysisConfig(
        enabled=True,
        require_min_alleles=2,
        compare_pocket_signatures=True,
        compare_tolerance_fingerprints=True,
        compare_anchor_patterns=True,
        use_combined_similarity=True,
        numeric_metric="euclidean",
        set_based_metric="jaccard",
        standardize_numeric_features=True,
    )
    result = run_cross_allele_analysis(allele_df, pd.DataFrame(), pd.DataFrame(), config, tmp_path)
    assert result.ran is False
