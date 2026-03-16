from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.retrospective_reporting import build_retrospective_report
from src.pattern_synthesis import synthesize_patterns
from src.workspace import WorkspaceConfig, load_workspace_config

@pytest.fixture
def mock_workspace_retro(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    memory_dir = workspace_dir / "program_memory"
    memory_dir.mkdir()
    
    # Create some dummy data for synthesis
    pd.DataFrame([
        {"rationale_category": "stronger_evidence", "outcome_class": "tested_followup", "count": 5},
    ]).to_csv(memory_dir / "rationale_to_outcome_patterns.csv", index=False)
    
    # Needs these non-empty to trigger synthesis logic
    pd.DataFrame([{"entity_id": "var1"}]).to_csv(memory_dir / "rationale_lineage.csv", index=False)
    pd.DataFrame([{"outcome_id": "out1"}]).to_csv(memory_dir / "outcomes_log.csv", index=False)

    pd.DataFrame([
        {"metric": "total_tasks", "value": 10},
        {"metric": "completed_tasks", "value": 5},
    ]).to_csv(memory_dir / "execution_metrics.csv", index=False)

    workspace_file = tmp_path / "workspace_retro.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "test_ws_retro",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "p1", "path": "p1_path"}]
    }))
    
    (tmp_path / "p1_path").mkdir()
    
    return workspace_file


def test_retrospective_flow(mock_workspace_retro: Path):
    # 1. Patterns
    config = load_workspace_config(mock_workspace_retro)
    patterns = synthesize_patterns(config.output_dir)
    assert not patterns["pattern_synthesis.csv"].empty
    
    # 2. Report
    report_out = build_retrospective_report(mock_workspace_retro, "monthly_program_retrospective", "retro_001")
    assert "retrospective_report.md" in report_out
    assert report_out["retrospective_report.md"].exists()
    
    # Check if role views were generated
    assert any("retrospective_manager.md" in str(p) for p in report_out.values())
    assert any("meeting_outline.md" in str(p) for p in report_out.values())
