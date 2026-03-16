from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.rationale_tracking import build_rationale_tracking
from src.workspace import WorkspaceConfig


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project_a"
    project_dir.mkdir()
    
    # Cycle 1: week_1
    week1_dir = project_dir / "review_packets" / "week_1" / "review_packet_tables"
    week1_dir.mkdir(parents=True)
    pd.DataFrame([
        {"entity_id": "var1", "rationale": "Strong evidence", "review_status": "shortlisted"},
        {"entity_id": "var2", "rationale": "Thin", "review_status": "shortlisted"},
        {"entity_id": "var3", "rationale": "", "review_status": "uncertain"},
    ]).to_csv(week1_dir / "shortlist.csv", index=False)
    
    # Cycle 2: current (review/shortlist.csv)
    current_dir = project_dir / "review"
    current_dir.mkdir()
    pd.DataFrame([
        {"entity_id": "var1", "rationale": "Stronger evidence after review", "review_status": "experimental_followup"},
        {"entity_id": "var2", "rationale": "Thin", "review_status": "rejected"}, # Status changed, rationale didn't (Conflict)
        {"entity_id": "var3", "rationale": "Still uncertain", "review_status": "uncertain"}, # Rationale changed, status didn't (Fine)
        {"entity_id": "var4", "rationale": "New item", "review_status": "shortlisted"},
    ]).to_csv(current_dir / "shortlist.csv", index=False)
    
    workspace_file = tmp_path / "workspace.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "test_workspace",
        "output_dir": str(tmp_path / "outputs"),
        "projects": [{"project_id": "proj_a", "path": str(project_dir)}]
    }))
    return workspace_file


def test_rationale_quality_metrics(mock_workspace: Path):
    outputs = build_rationale_tracking(mock_workspace)
    lineage_df = pd.read_csv(outputs["rationale_lineage.csv"])
    print("\nLineage DataFrame:\n", lineage_df[["entity_id", "cycle_id", "rationale_text", "rationale_completeness"]])
    
    # Check for completeness
    var3_week1 = lineage_df[(lineage_df["entity_id"] == "var3") & (lineage_df["cycle_id"] == "week_1")].iloc[0]
    assert var3_week1["rationale_completeness"] == False
    
    # Check for length/thinness
    assert "rationale_length" in lineage_df.columns
    assert "is_thin_rationale" in lineage_df.columns
    # "Thin" is 1 word, should be thin if threshold is > 1
    assert lineage_df[lineage_df["entity_id"] == "var2"].iloc[0]["is_thin_rationale"] == True
    
    # Check for conflict (silent change)
    assert "is_silent_status_change" in lineage_df.columns
    var2_current = lineage_df[(lineage_df["entity_id"] == "var2") & (lineage_df["cycle_id"] == "current")].iloc[0]
    assert var2_current["is_silent_status_change"] == True


from src.outcomes import import_outcomes, summarize_outcomes

def test_rationale_outcome_alignment(tmp_path: Path):
    project_dir = tmp_path / "project_b"
    project_dir.mkdir()
    
    # Review: current
    current_dir = project_dir / "review"
    current_dir.mkdir()
    pd.DataFrame([
        {"entity_id": "var1", "rationale": "Shortlisted", "review_status": "shortlisted"},
        {"entity_id": "var2", "rationale": "Rejected", "review_status": "rejected"},
    ]).to_csv(current_dir / "shortlist.csv", index=False)
    
    workspace_file = tmp_path / "workspace_b.yaml"
    workspace_config = {
        "workspace_id": "test_workspace_b",
        "output_dir": str(tmp_path / "outputs_b"),
        "projects": [{"project_id": "proj_b", "path": str(project_dir)}]
    }
    workspace_file.write_text(yaml.dump(workspace_config))
    
    # Import an outcome for var2 (rejected in review but somehow tested)
    outcome_file = tmp_path / "outcomes.csv"
    pd.DataFrame([
        {
            "outcome_id": "out1",
            "entity_type": "variant",
            "entity_id": "var2",
            "project_id": "proj_b",
            "workspace_id": "test_workspace_b",
            "cycle_id": "current",
            "outcome_class": "tested_followup",
            "outcome_source": "external",
            "outcome_timestamp": "2026-03-15T00:00:00Z",
            "outcome_notes": "Tested anyway",
            "linked_artifacts": "",
            "reviewer_or_owner": "scientist",
            "confidence_in_outcome_context": "high",
            "not_model_truth_flag": True
        }
    ]).to_csv(outcome_file, index=False)
    
    import_outcomes(workspace_file, outcome_file)
    outputs = summarize_outcomes(workspace_file)
    
    aware_df = pd.read_csv(outputs["outcome_aware_decision_summary.csv"])
    
    # Check for alignment columns
    assert "is_decision_outcome_divergent" in aware_df.columns
    var2_row = aware_df[aware_df["entity_id"] == "var2"].iloc[0]
    assert var2_row["is_decision_outcome_divergent"] == True
