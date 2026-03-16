from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.portfolio_aggregation import build_portfolio_aggregation
from src.portfolio_prioritization import build_portfolio_prioritization
from src.attention_queue import build_attention_queues
from src.portfolio_compare import compare_portfolio_modes


@pytest.fixture
def mock_workspace_portfolio(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    memory_dir = workspace_dir / "program_memory"
    memory_dir.mkdir()
    
    # Mock some data for portfolio
    pd.DataFrame([
        {"entity_id": "v1", "analytical_robustness_label": "robust_across_playbooks", "human_robustness_label": "consensus_robust", "combined_status": "strong_candidate_with_human_alignment"},
        {"entity_id": "v2", "analytical_robustness_label": "moderately_stable", "human_robustness_label": "disputed_judgment", "combined_status": "requires_more_review"},
        {"entity_id": "v3", "analytical_robustness_label": "fragile_to_assumptions", "human_robustness_label": "consensus_fragile", "combined_status": "requires_more_evidence"},
    ]).to_csv(memory_dir / "combined_robustness.csv", index=False)

    pd.DataFrame([
        {"entity_id": "v1", "project_id": "proj1", "latest_seen_review": "week1", "current_status": "shortlisted"},
        {"entity_id": "v2", "project_id": "proj1", "latest_seen_review": "week1", "current_status": "shortlisted"},
        {"entity_id": "v3", "project_id": "proj2", "latest_seen_review": "week2", "current_status": "shortlisted"},
    ]).to_csv(memory_dir / "multicycle_decision_summary.csv", index=False)

    project_dir = tmp_path / "dummy_proj"
    project_dir.mkdir()

    workspace_file = tmp_path / "workspace_p20.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "ws_p20",
        "name": "Phase 20 Workspace",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "dummy", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_portfolio_planning_flow(mock_workspace_portfolio: Path):
    config = load_workspace_config(mock_workspace_portfolio)
    
    # 1. Aggregation
    agg_res = build_portfolio_aggregation(config)
    assert agg_res["portfolio_candidates.csv"].exists()
    
    # 2. Prioritization
    prio_res = build_portfolio_prioritization(config, "evidence_first_capacity_mode")
    assert prio_res["portfolio_prioritization.csv"].exists()
    df = pd.read_csv(prio_res["portfolio_prioritization.csv"])
    assert "priority_bucket" in df.columns
    assert "do_now" in df["priority_bucket"].values
    
    # 3. Queues
    queue_res = build_attention_queues(config)
    assert queue_res["scientist_attention_queue.csv"].exists()
    assert queue_res["escalation_queue.csv"].exists()
    
    # 4. Compare
    comp_res = compare_portfolio_modes(config, "evidence_first_capacity_mode", "consensus_first_capacity_mode")
    assert comp_res["portfolio_mode_comparison.csv"].exists()
