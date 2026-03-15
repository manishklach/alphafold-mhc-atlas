from pathlib import Path
import shutil

import pandas as pd

from src.project_index import load_project_tables
from src.review_queue import create_review_queue_from_scenario, update_review_item
from src.scenario_analysis import run_scenario_analysis
from src.scenario_state import ScenarioState
from src.shortlist import refresh_shortlists


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/cross_allele_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def _scenario() -> ScenarioState:
    return ScenarioState(
        scenario_id="disruptive_demo",
        label="Disruptive Demo",
        ranking_mode="disruptive_mutations",
        alleles=[],
        peptides=[],
        mutation_positions=[],
        substitutions=[],
        evidence_coverage_threshold=0.0,
        allowed_uncertainty=["low", "moderate", "high", "insufficient_data"],
        require_structural_support=False,
        anchor_only=False,
        case_study_id=None,
        panel_size=10,
        notes="",
    )


def test_review_queue_and_shortlist_flow(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    tables = load_project_tables(project)
    result = run_scenario_analysis(_scenario(), tables)
    create_review_queue_from_scenario(project, result, reviewer="alice")
    queue_df = pd.read_csv(project / "review" / "review_queue.csv")
    assert not queue_df.empty
    entity_id = str(queue_df.iloc[0]["entity_id"])
    update_review_item(project, entity_id, "shortlisted", reviewer="alice", rationale="Good follow-up")
    refresh_shortlists(project)
    shortlist_df = pd.read_csv(project / "review" / "shortlist.csv")
    assert entity_id in shortlist_df["entity_id"].astype(str).tolist()
