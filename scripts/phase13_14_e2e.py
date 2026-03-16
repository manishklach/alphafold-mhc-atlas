from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import yaml
from datetime import datetime, timezone

from src.workspace import load_workspace_config
from src.execution_plan import build_execution_plan
from src.execution_bundle import build_execution_bundle
from src.ownership import assign_ownership
from src.status_tracking import update_task_status
from src.pattern_synthesis import synthesize_patterns
from src.retrospective_reporting import build_retrospective_report
from src.action_outcome_trace import build_action_outcome_trace

def run_e2e():
    root = Path("e2e_test_workspace")
    root.mkdir(exist_ok=True)
    
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    project_dir = root / "project_alpha"
    project_dir.mkdir(exist_ok=True)
    
    # 1. Setup Phase 11/12 State
    (project_dir / "review").mkdir(exist_ok=True)
    (project_dir / "analysis").mkdir(exist_ok=True)
    
    # Shortlist
    pd.DataFrame([
        {"entity_id": "var_001", "review_status": "shortlisted", "rationale": "High binding confidence"},
        {"entity_id": "var_002", "review_status": "shortlisted", "rationale": "Novel pocket interaction"},
    ]).to_csv(project_dir / "review" / "shortlist.csv", index=False)
    
    # Outcomes (Phase 12)
    memory_dir = outputs_dir / "program_memory"
    memory_dir.mkdir(exist_ok=True)
    pd.DataFrame([
        {
            "outcome_id": "out_1",
            "entity_type": "shortlist_item",
            "entity_id": "var_001",
            "outcome_class": "tested_followup",
            "outcome_notes": "Promising wet-lab result",
            "outcome_source": "manual",
            "outcome_timestamp": datetime.now(timezone.utc).isoformat(),
            "linked_artifacts": ""
        },
    ]).to_csv(memory_dir / "outcomes_log.csv", index=False)
    
    # Workspace Config
    workspace_file = root / "workspace.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "e2e_test_ws",
        "name": "E2E Test Workspace",
        "description": "Validating Phase 13 and 14",
        "projects": [{"project_id": "alpha", "path": str(project_dir.resolve())}],
        "output_dir": str(outputs_dir.resolve())
    }))
    
    print("--- Phase 13: Operational Planning ---")
    # Build Plan
    plan_results = build_execution_plan(workspace_file, "shortlist_to_followup_plan", "e2e_plan_v1")
    print(f"Plan built at: {plan_results['plan_dir']}")
    
    # Build Bundle
    bundle_path = build_execution_bundle(workspace_file, "e2e_plan_v1", "e2e_bundle_v1")
    print(f"Bundle created at: {bundle_path}")
    
    # Assign and Update
    tasks_df = pd.read_csv(plan_results["followup_tasks.csv"])
    task_id = tasks_df.iloc[0]["task_id"]
    assign_ownership(workspace_file, task_id, "Dr. Atlas", "scientist", "Priority check")
    update_task_status(workspace_file, task_id, "completed", "Verified in wet lab")
    print(f"Task {task_id} assigned and completed.")
    
    print("\n--- Phase 14: Retrospective Synthesis ---")
    # Action-Outcome Trace
    trace_results = build_action_outcome_trace(workspace_file)
    print(f"Trace built: {trace_results['action_outcome_trace.csv']}")
    
    # Patterns
    pattern_results = synthesize_patterns(outputs_dir)
    print(f"Patterns synthesized: {pattern_results['pattern_digest.md']}")
    
    # Retrospective Report
    retro_results = build_retrospective_report(workspace_file, "quarterly_workspace_retrospective", "e2e_retro_v1")
    print(f"Retrospective Report: {retro_results['retrospective_report.md']}")
    
    print("\nE2E Test Successful!")
    print(f"Final Report Path: {retro_results['retrospective_report.md']}")

if __name__ == "__main__":
    run_e2e()
