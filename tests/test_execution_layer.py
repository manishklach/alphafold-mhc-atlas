from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.execution_plan import build_execution_plan
from src.execution_bundle import build_execution_bundle
from src.ownership import assign_ownership
from src.status_tracking import update_task_status
from src.action_outcome_trace import build_action_outcome_trace
from src.execution_metrics import summarize_execution_metrics

@pytest.fixture
def mock_workspace_execution(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project_exec"
    project_dir.mkdir()
    
    # review/shortlist.csv
    review_dir = project_dir / "review"
    review_dir.mkdir()
    pd.DataFrame([
        {"entity_id": "var1", "rationale": "Strong evidence", "review_status": "shortlisted"},
    ]).to_csv(review_dir / "shortlist.csv", index=False)

    # analysis/next_action_table.csv & open_questions.csv
    analysis_dir = project_dir / "analysis"
    analysis_dir.mkdir()
    pd.DataFrame([
        {"entity_id": "var1", "action_type": "request_domain_input", "rationale": "Need expert", "owner_role_suggestion": "scientist"},
    ]).to_csv(analysis_dir / "next_action_table.csv", index=False)

    pd.DataFrame([
        {"question_id": "q_1", "question_text": "Is this real?"},
    ]).to_csv(analysis_dir / "open_questions.csv", index=False)
    
    workspace_file = tmp_path / "workspace_exec.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "test_ws_exec",
        "output_dir": str(tmp_path / "outputs"),
        "projects": [{"project_id": "proj_exec", "path": str(project_dir)}]
    }))
    
    return workspace_file


def test_execution_plan_and_bundle(mock_workspace_execution: Path):
    # 1. Build plan
    plan_out = build_execution_plan(mock_workspace_execution, "shortlist_to_followup_plan", "plan_001")
    
    tasks_df = pd.read_csv(plan_out["followup_tasks.csv"])
    assert not tasks_df.empty
    assert "task_id" in tasks_df.columns
    
    # Should have tasks for shortlist_item and next_action
    assert "shortlist_item" in tasks_df["entity_type"].values
    assert "next_action" in tasks_df["entity_type"].values

    # 2. Build bundle
    bundle_dir = build_execution_bundle(mock_workspace_execution, "plan_001", "bundle_001")
    assert (bundle_dir / "execution_brief.md").exists()
    assert (bundle_dir / "selected_variants.csv").exists()
    
    # 3. Assign ownership
    task_id = tasks_df.iloc[0]["task_id"]
    assign_ownership(mock_workspace_execution, task_id, "Dr. Smith", "scientist", "Please look")
    updated_tasks = pd.read_csv(plan_out["followup_tasks.csv"])
    assert updated_tasks.loc[updated_tasks["task_id"] == task_id, "owner"].iloc[0] == "Dr. Smith"
    
    # 4. Update status
    update_task_status(mock_workspace_execution, task_id, "completed", "Done it")
    updated_tasks2 = pd.read_csv(plan_out["followup_tasks.csv"])
    assert updated_tasks2.loc[updated_tasks2["task_id"] == task_id, "status"].iloc[0] == "completed"

    # 5. Metrics
    metrics = summarize_execution_metrics(mock_workspace_execution)
    m_df = pd.read_csv(metrics["execution_metrics.csv"])
    assert not m_df.empty

    # 6. Action-to-outcome trace
    trace = build_action_outcome_trace(mock_workspace_execution)
    trace_df = pd.read_csv(trace["action_outcome_trace.csv"])
    assert "not_model_truth_flag" in trace_df.columns
