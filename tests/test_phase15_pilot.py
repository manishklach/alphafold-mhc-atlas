from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.pilot_deployment import check_pilot_readiness
from src.setup_pack import create_setup_pack
from src.role_workflows import export_role_workflows
from src.evaluation_pack import create_evaluation_pack
from src.workspace_evaluation import build_workspace_evaluation_sequence

@pytest.fixture
def mock_workspace_pilot(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    memory_dir = workspace_dir / "program_memory"
    memory_dir.mkdir()
    
    # Needs memory to pass readiness checks
    pd.DataFrame([{"cycle_id": "c1", "entity_id": "v1"}]).to_csv(memory_dir / "decision_lineage.csv", index=False)

    project_dir = tmp_path / "p1"
    project_dir.mkdir()

    workspace_file = tmp_path / "workspace_pilot.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "test_ws_pilot",
        "name": "Test Pilot",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "p1", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_pilot_deployment_layer(mock_workspace_pilot: Path):
    # 1. Readiness
    readiness = check_pilot_readiness(mock_workspace_pilot)
    assert readiness["pilot_readiness_report.md"].exists()
    
    with open(readiness["pilot_readiness_summary.json"]) as f:
        import json
        summary = json.load(f)
        assert summary["is_ready"] is True

    # 2. Setup Pack
    pack = create_setup_pack(mock_workspace_pilot, "pack_001")
    assert pack["setup_pack_readme.md"].exists()
    assert pack["workspace_config_copy.yaml"].exists()

    # 3. Role Workflows
    roles = export_role_workflows(mock_workspace_pilot)
    assert roles["role_workflow_manifest.csv"].exists()
    assert "role_workflow_manager.md" in roles

    # 4. Evaluation Pack
    eval_pack = create_evaluation_pack(mock_workspace_pilot)
    assert eval_pack["PILOT_EVALUATION_GUIDE.md"].exists()

    # 5. Workspace Evaluation Sequence
    ws_eval = build_workspace_evaluation_sequence(mock_workspace_pilot)
    assert ws_eval["workspace_evaluation_plan.md"].exists()
    assert ws_eval["evaluator_day1.md"].exists()
    
    seq_df = pd.read_csv(ws_eval["evaluation_sequence.csv"])
    assert not seq_df.empty
