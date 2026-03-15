import pandas as pd

from src.config import DiversityConstraintsConfig, PanelDesignConfig
from src.panel_design import run_panel_design


def test_panel_design_respects_diversity_constraints() -> None:
    priority_df = pd.DataFrame(
        [
            {"variant_id": "v1", "allele_name": "A", "mutant_peptide": "P1", "mutated_position": 2, "mut_residue": "A", "priority_score": 5.0, "evidence_coverage_score": 0.9, "uncertainty_flag": "low", "ranking_mode": "balanced_exploration_panel"},
            {"variant_id": "v2", "allele_name": "A", "mutant_peptide": "P2", "mutated_position": 2, "mut_residue": "V", "priority_score": 4.5, "evidence_coverage_score": 0.9, "uncertainty_flag": "low", "ranking_mode": "balanced_exploration_panel"},
            {"variant_id": "v3", "allele_name": "B", "mutant_peptide": "P3", "mutated_position": 9, "mut_residue": "F", "priority_score": 4.0, "evidence_coverage_score": 0.8, "uncertainty_flag": "moderate", "ranking_mode": "balanced_exploration_panel"},
        ]
    )
    config = PanelDesignConfig(
        enabled=True,
        max_panel_size=2,
        ranking_goal="balanced_exploration_panel",
        require_min_evidence_coverage=0.5,
        penalize_high_uncertainty=True,
        diversity_constraints=DiversityConstraintsConfig(
            max_variants_per_position=1,
            max_variants_per_allele=2,
            max_variants_per_substitution=1,
        ),
        redundancy_features=["allele_name", "mutated_position", "mut_residue"],
    )

    result = run_panel_design(priority_df, config)

    selected = result.balanced_panel_df["variant_id"].tolist()
    assert "v1" in selected
    assert "v2" not in selected
    assert len(selected) <= 2
