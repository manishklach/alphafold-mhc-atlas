from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.executive_brief import generate_executive_brief
from src.final_handoff import build_final_handoff


@pytest.fixture
def mock_workspace_phase19(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    memory_dir = workspace_dir / "program_memory"
    memory_dir.mkdir()
    
    # Mock combined robustness data from Phase 18
    pd.DataFrame([
        {"entity_id": "v1", "combined_status": "strong_candidate_with_human_alignment"},
        {"entity_id": "v2", "combined_status": "analytically_stable_but_humanly_disputed"},
        {"entity_id": "v3", "combined_status": "requires_more_evidence"},
    ]).to_csv(memory_dir / "combined_robustness.csv", index=False)

    project_dir = tmp_path / "dummy_proj"
    project_dir.mkdir()

    workspace_file = tmp_path / "workspace_p19.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "ws_p19",
        "name": "Phase 19 Workspace",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "dummy", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_executive_handoff_flow(mock_workspace_phase19: Path):
    config = load_workspace_config(mock_workspace_phase19)
    
    # 1. Generate Executive Brief
    brief_res = generate_executive_brief(config, "test_brief")
    assert brief_res["executive_brief.md"].exists()
    
    # Read the brief to ensure v1 and v2 are mentioned
    content = brief_res["executive_brief.md"].read_text(encoding="utf-8")
    assert "v1" in content
    assert "v2" in content
    assert "v3" not in content  # v3 is requires_more_evidence, shouldn't be highlighted
    
    # 2. Build Final Handoff
    handoff_res = build_final_handoff(config, "test_handoff")
    assert handoff_res["executive_brief.md"].exists()
    assert handoff_res["consensus_robust_candidates.csv"].exists()
    assert handoff_res["evidence_manifest.csv"].exists()
    assert handoff_res["caveats_and_limitations.md"].exists()
    
    # Check candidates CSV
    df = pd.read_csv(handoff_res["consensus_robust_candidates.csv"])
    assert len(df) == 1
    assert df["entity_id"].iloc[0] == "v1"
