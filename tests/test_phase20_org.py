from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.org_aggregation import aggregate_organization_data, write_org_aggregation
from src.org_retrospective import build_org_retrospective
from src.operating_review_packet import build_operating_review_packet


@pytest.fixture
def mock_org_environment(tmp_path: Path) -> Path:
    ws_root = tmp_path / "workspaces"
    ws_root.mkdir()
    
    # Create WS 1
    ws1_dir = tmp_path / "ws1_out"
    ws1_dir.mkdir()
    (ws1_dir / "portfolio").mkdir()
    pd.DataFrame([
        {"entity_id": "v1", "priority_bucket": "do_now"},
        {"entity_id": "v2", "priority_bucket": "monitor"},
    ]).to_csv(ws1_dir / "portfolio" / "portfolio_prioritization.csv", index=False)
    pd.DataFrame([{"project_id": "p1"}]).to_csv(ws1_dir / "workspace_projects.csv", index=False)
    
    ws1_file = ws_root / "ws1.yaml"
    ws1_file.write_text(yaml.dump({
        "workspace_id": "ws1",
        "output_dir": str(ws1_dir),
        "projects": [{"project_id": "p1", "path": "some_path"}]
    }))

    # Create WS 2
    ws2_dir = tmp_path / "ws2_out"
    ws2_dir.mkdir()
    (ws2_dir / "portfolio").mkdir()
    pd.DataFrame([
        {"entity_id": "v3", "priority_bucket": "do_now"},
    ]).to_csv(ws2_dir / "portfolio" / "portfolio_prioritization.csv", index=False)
    pd.DataFrame([{"project_id": "p2"}]).to_csv(ws2_dir / "workspace_projects.csv", index=False)
    
    ws2_file = ws_root / "ws2.yaml"
    ws2_file.write_text(yaml.dump({
        "workspace_id": "ws2",
        "output_dir": str(ws2_dir),
        "projects": [{"project_id": "p2", "path": "some_path"}]
    }))
    
    return ws_root


def test_org_aggregation_and_reporting(mock_org_environment: Path):
    output_dir = mock_org_environment.parent / "org_outputs"
    
    # 1. Aggregate
    results = write_org_aggregation(mock_org_environment, output_dir)
    assert results["org_portfolio_summary.csv"].exists()
    
    df = pd.read_csv(results["org_portfolio_summary.csv"])
    assert len(df) == 3
    assert set(df["workspace_id"]) == {"ws1", "ws2"}
    
    # 2. Retrospective
    retro = build_org_retrospective(mock_org_environment, output_dir)
    assert retro["org_retrospective_report.md"].exists()
    content = retro["org_retrospective_report.md"].read_text(encoding="utf-8")
    assert "Portfolio Overview" in content
    # In src/org_retrospective.py, we check workpaces covered from proj_df['workspace_id'].unique()
    assert "Workspaces covered: 2" in content
    
    # 3. Operating Review Packet
    packet = build_operating_review_packet(mock_org_environment, output_dir, "test_packet")
    assert packet["operating_review.md"].exists()
    assert (output_dir / "operating_review_packets" / "test_packet" / "org_retrospective_report.md").exists()
