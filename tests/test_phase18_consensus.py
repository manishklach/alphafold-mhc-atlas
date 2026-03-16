from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.reviewer_judgments import import_reviewer_judgments, summarize_judgments
from src.consensus_analysis import build_consensus_summaries
from src.disagreement_drivers import analyze_disagreement_drivers
from src.human_robustness import build_human_robustness_summary
from src.combined_robustness import build_combined_robustness
from src.reviewer_packs import create_reviewer_pack
from src.consensus_meeting import create_consensus_meeting_pack

@pytest.fixture
def mock_workspace_phase18(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "outputs"
    workspace_dir.mkdir()
    memory_dir = workspace_dir / "program_memory"
    memory_dir.mkdir()
    
    # Mock some existing data
    pd.DataFrame([
        {"entity_id": "v1", "current_status": "shortlisted"},
        {"entity_id": "v2", "current_status": "shortlisted"},
    ]).to_csv(memory_dir / "multicycle_decision_summary.csv", index=False)

    pd.DataFrame([
        {"entity_id": "v1", "robustness_label": "robust_across_playbooks"},
        {"entity_id": "v2", "robustness_label": "fragile_to_assumptions"},
    ]).to_csv(memory_dir / "robustness_summary.csv", index=False)

    # Mock judgments CSV to import
    judgments_csv = tmp_path / "test_judgments.csv"
    pd.DataFrame([
        {"entity_type": "variant", "entity_id": "v1", "reviewer_name": "R1", "reviewer_role": "scientist", "judgment_label": "prioritize", "reviewer_confidence": "high", "playbook_id": "pb1", "benchmark_mode": "blind"},
        {"entity_type": "variant", "entity_id": "v1", "reviewer_name": "R2", "reviewer_role": "manager", "judgment_label": "prioritize", "reviewer_confidence": "high", "playbook_id": "pb1", "benchmark_mode": "blind"},
        {"entity_type": "variant", "entity_id": "v2", "reviewer_name": "R1", "reviewer_role": "scientist", "judgment_label": "prioritize", "reviewer_confidence": "high", "playbook_id": "pb1", "benchmark_mode": "blind"},
        {"entity_type": "variant", "entity_id": "v2", "reviewer_name": "R2", "reviewer_role": "manager", "judgment_label": "deprioritize", "reviewer_confidence": "low", "playbook_id": "pb2", "benchmark_mode": "aware"},
    ]).to_csv(judgments_csv, index=False)

    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()

    workspace_file = tmp_path / "workspace_p18.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "ws_p18",
        "name": "Phase 18 Workspace",
        "output_dir": str(workspace_dir),
        "projects": [{"project_id": "dummy", "path": str(project_dir)}]
    }))
    
    return workspace_file, judgments_csv


def test_consensus_flow(mock_workspace_phase18: tuple[Path, Path]):
    ws_file, judgments_csv = mock_workspace_phase18
    config = load_workspace_config(ws_file)
    
    # 1. Import
    log_path = import_reviewer_judgments(config, judgments_csv)
    assert log_path.exists()
    
    # 2. Summarize
    summarize_judgments(config)
    
    # 3. Consensus
    con = build_consensus_summaries(config)
    assert "consensus_summary.csv" in con
    
    # 4. Drivers
    dr = analyze_disagreement_drivers(config)
    assert "disagreement_drivers.csv" in dr
    
    # 5. Human Robustness
    hr = build_human_robustness_summary(config)
    assert "human_robustness_summary.csv" in hr
    
    # 6. Combined Robustness
    cr = build_combined_robustness(config)
    assert "combined_robustness.csv" in cr
    
    df = pd.read_csv(cr["combined_robustness.csv"])
    # v1 should be strong_candidate_with_human_alignment (robust + consensus_robust)
    assert df[df["entity_id"] == "v1"]["combined_status"].iloc[0] == "strong_candidate_with_human_alignment"
    
    # 7. Reviewer Pack
    rp = create_reviewer_pack(config, "pack_1")
    assert (rp / "reviewer_pack_readme.md").exists()
    
    # 8. Meeting Pack
    mp = create_consensus_meeting_pack(config, "meeting_1")
    assert (mp / "consensus_brief.md").exists()
