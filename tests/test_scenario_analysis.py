import pandas as pd

from src.scenario_analysis import compare_scenarios, run_scenario_analysis
from src.scenario_state import ScenarioState


def test_run_scenario_analysis_filters_priority_rows_and_exports_summary(tmp_path) -> None:
    tables = {
        "priority": pd.DataFrame(
            [
                {
                    "variant_id": "v1",
                    "allele_name": "HLA-A*02:01",
                    "mutant_peptide": "AAA",
                    "mutated_position": 2,
                    "mut_residue": "A",
                    "ranking_mode": "disruptive_mutations",
                    "evidence_coverage_score": 0.8,
                    "uncertainty_flag": "low",
                    "structural_support_status": "available",
                    "priority_rank": 1,
                    "priority_score": 1.2,
                },
                {
                    "variant_id": "v2",
                    "allele_name": "HLA-B*07:02",
                    "mutant_peptide": "BBB",
                    "mutated_position": 9,
                    "mut_residue": "F",
                    "ranking_mode": "disruptive_mutations",
                    "evidence_coverage_score": 0.4,
                    "uncertainty_flag": "high",
                    "structural_support_status": "missing",
                    "priority_rank": 2,
                    "priority_score": 0.6,
                },
            ]
        ),
        "panel": pd.DataFrame([{"panel_id": "p1", "variant_id": "v1", "allele_name": "HLA-A*02:01", "mutated_position": 2, "substitution": "A"}]),
        "priority_evidence": pd.DataFrame([{"variant_id": "v1", "evidence_name": "delta_total_contacts_vs_wt"}]),
    }
    scenario = ScenarioState(
        scenario_id="s1",
        label="Disruptive shortlist",
        ranking_mode="disruptive_mutations",
        alleles=["HLA-A*02:01"],
        peptides=[],
        mutation_positions=[2],
        substitutions=["A"],
        evidence_coverage_threshold=0.5,
        allowed_uncertainty=["low", "moderate"],
        require_structural_support=True,
        anchor_only=False,
        case_study_id=None,
        panel_size=5,
        notes="",
    )

    result = run_scenario_analysis(scenario, tables, tmp_path)

    assert result["summary"]["num_ranked_variants"] == 1
    assert result["ranked_variants"].iloc[0]["variant_id"] == "v1"
    assert (tmp_path / "scenario_summary.csv").exists()


def test_compare_scenarios_builds_rank_and_panel_diffs() -> None:
    scenario_a = {
        "scenario": {"scenario_id": "a"},
        "ranked_variants": pd.DataFrame([{"variant_id": "v1", "priority_rank": 1, "priority_score": 1.0}]),
        "panel": pd.DataFrame([{"variant_id": "v1"}]),
    }
    scenario_b = {
        "scenario": {"scenario_id": "b"},
        "ranked_variants": pd.DataFrame([{"variant_id": "v2", "priority_rank": 1, "priority_score": 0.9}]),
        "panel": pd.DataFrame([{"variant_id": "v2"}]),
    }

    result = compare_scenarios(scenario_a, scenario_b)

    assert not result["rank_diff"].empty
    assert not result["panel_diff"].empty
