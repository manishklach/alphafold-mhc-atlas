from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.playbook_schema import load_playbooks, get_playbook
from src.scenario_playbooks import run_playbook
from src.sensitivity_testing import run_sensitivity_suite
from src.decision_robustness import compute_decision_robustness
from src.playbook_compare import compare_playbooks

@pytest.fixture
def mock_workspace_phase17(tmp_path: Path) -> Path:
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    analysis_dir = project_dir / "analysis"
    analysis_dir.mkdir()
    
    # Priority Data
    pd.DataFrame([
        {"variant_id": "v1", "allele_name": "A0201", "priority_score": 10.0, "priority_rank": 1, "ranking_mode": "disruptive_mutations", "evidence_coverage_score": 0.9, "structural_support_status": "available"},
        {"variant_id": "v2", "allele_name": "A0201", "priority_score": 8.0, "priority_rank": 2, "ranking_mode": "disruptive_mutations", "evidence_coverage_score": 0.7, "structural_support_status": "available"},
        {"variant_id": "v3", "allele_name": "A0201", "priority_score": 5.0, "priority_rank": 3, "ranking_mode": "disruptive_mutations", "evidence_coverage_score": 0.4, "structural_support_status": "available"},
    ]).to_csv(analysis_dir / "variant_priority_table.csv", index=False)

    workspace_file = tmp_path / "workspace_p17.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "ws_p17",
        "name": "Phase 17 Workspace",
        "output_dir": str(tmp_path / "outputs"),
        "projects": [{"project_id": "p1", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_playbook_and_robustness_flow(mock_workspace_phase17: Path):
    from src.workspace_index import build_workspace_inventory
    from src.cli import _combine_project_tables
    
    config = load_workspace_config(mock_workspace_phase17)
    inventory = build_workspace_inventory(config)
    tables = _combine_project_tables(inventory)
    
    # 1. Playbook run
    res = run_playbook(config.output_dir, "conservative_binder", tables)
    assert not res["ranked_variants"].empty
    # v3 should be filtered out by threshold 0.8
    assert "v3" not in res["ranked_variants"]["variant_id"].values

    # 2. Sensitivity Suite
    sens = run_sensitivity_suite(config.output_dir, "conservative_binder", tables)
    assert len(sens["runs"]) > 1
    
    # 3. Robustness
    rob = compute_decision_robustness(sens["results"], config.output_dir / "robustness")
    assert "robustness_summary.csv" in rob
    df = rob["robustness_summary.csv"]
    assert "v1" in df["entity_id"].values

    # 4. Playbook Compare
    comp = compare_playbooks(config.output_dir, "conservative_binder", "viral_escape_explorer", tables)
    assert "rank_diff" in comp
