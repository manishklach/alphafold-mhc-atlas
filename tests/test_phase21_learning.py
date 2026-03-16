from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml
import json

from src.workspace import load_workspace_config
from src.pilot_usage import log_pilot_event, aggregate_usage_data, summarize_usage
from src.workflow_adoption import summarize_workflow_adoption
from src.usage_friction import summarize_usage_friction
from src.pilot_health import summarize_pilot_health
from src.product_learning_packet import build_product_learning_packet


@pytest.fixture
def mock_workspace_phase21(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    
    project_dir = tmp_path / "p1"
    project_dir.mkdir()

    workspace_file = tmp_path / "workspace_p21.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "ws_p21",
        "name": "Phase 21 Workspace",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "p1", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_pilot_learning_flow(mock_workspace_phase21: Path):
    config = load_workspace_config(mock_workspace_phase21)
    
    # 1. Log events
    log_pilot_event(config, "workspace_opened", surface="cli")
    log_pilot_event(config, "page_viewed", surface="app", artifact_id="Overview")
    log_pilot_event(config, "review_packet_generated", surface="app")
    
    # 2. Aggregate
    df = aggregate_usage_data(config)
    assert len(df) == 3
    assert "event_type" in df.columns
    
    # 3. Summarize Components
    summarize_usage(config)
    summarize_workflow_adoption(config)
    summarize_usage_friction(config)
    summarize_pilot_health(config)
    
    learning_dir = config.output_dir / "pilot_learning"
    assert (learning_dir / "usage_summary.csv").exists()
    assert (learning_dir / "workflow_adoption.csv").exists()
    assert (learning_dir / "friction_summary.csv").exists()
    assert (learning_dir / "pilot_health_summary.csv").exists()
    
    # 4. Product Learning Packet
    packet = build_product_learning_packet(config, "packet_test")
    assert packet["product_learning_summary.md"].exists()
    assert (packet["packet_dir"] / "usage_summary.csv").exists()
