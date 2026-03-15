from pathlib import Path
import shutil

from src.handoff_bundle import create_handoff_bundle
from src.project_index import load_project_tables
from src.review_queue import create_review_queue_from_scenario
from src.scenario_analysis import build_evidence_exports, export_scenario_result, run_scenario_analysis
from src.scenario_state import ScenarioState


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/cross_allele_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_handoff_bundle_includes_scope_statement(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    scenario = ScenarioState(
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
    tables = load_project_tables(project)
    result = run_scenario_analysis(scenario, tables)
    export_dir = project / "scenario_exports" / scenario.scenario_id
    export_scenario_result(result, export_dir)
    build_evidence_exports(result, tables, export_dir)
    bundle = create_handoff_bundle(project, "pilot_bundle", [scenario.scenario_id])
    text = (bundle / "README.md").read_text(encoding="utf-8")
    assert "Conservative by design" in text
    assert (bundle / "bundle_manifest.csv").exists()
