from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from .workspace import WorkspaceConfig, load_workspace_config
from .pilot_deployment import check_pilot_readiness
from .evaluation_pack import create_evaluation_pack
from .role_workflows import export_role_workflows

def build_workspace_evaluation_sequence(
    workspace: WorkspaceConfig | str | Path
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    output_dir = config.output_dir / "workspace_evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate supporting artifacts
    readiness = check_pilot_readiness(config)
    eval_pack = create_evaluation_pack(config)
    roles = export_role_workflows(config)
    
    # Overall Plan
    plan_path = output_dir / "workspace_evaluation_plan.md"
    plan_lines = [
        f"# Workspace Evaluation Plan: {config.name}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This plan outlines a recommended 1-2 week pilot sequence.",
        "",
        "## Readiness Status",
        f"- See `{readiness['pilot_readiness_report.md']}`",
        "",
        "## Evaluation Pack",
        f"- Main Guide: `{eval_pack['PILOT_EVALUATION_GUIDE.md']}`",
        "",
        "## Sequence",
        "See Day 1, Day 3, and Day 7 summaries."
    ]
    plan_path.write_text("\n".join(plan_lines), encoding="utf-8")
    
    # Day 1
    d1_path = output_dir / "evaluator_day1.md"
    d1_lines = [
        "# Day 1: Setup and Basics",
        "- Run setup pack and verify environment.",
        "- Read `PILOT_EVALUATION_GUIDE.md`.",
        "- Generate a workspace review packet.",
        "- Have scientists review shortlists."
    ]
    d1_path.write_text("\n".join(d1_lines), encoding="utf-8")

    # Day 3
    d3_path = output_dir / "evaluator_day3.md"
    d3_lines = [
        "# Day 3: Execution and Roles",
        "- Convert shortlists into an execution plan.",
        "- Review `role_workflow_manager.md`.",
        "- Assign follow-up tasks."
    ]
    d3_path.write_text("\n".join(d3_lines), encoding="utf-8")

    # Day 7
    d7_path = output_dir / "evaluator_day7.md"
    d7_lines = [
        "# Day 7: Outcomes and Retrospective",
        "- Update task status and record simulated outcomes.",
        "- Generate retrospective report.",
        "- Discuss evaluation questions."
    ]
    d7_path.write_text("\n".join(d7_lines), encoding="utf-8")

    # Sequence CSV
    seq_path = output_dir / "evaluation_sequence.csv"
    pd.DataFrame([
        {"day": 1, "focus": "Setup & Basics", "file": "evaluator_day1.md"},
        {"day": 3, "focus": "Execution & Roles", "file": "evaluator_day3.md"},
        {"day": 7, "focus": "Outcomes & Retrospective", "file": "evaluator_day7.md"}
    ]).to_csv(seq_path, index=False)
    
    return {
        "workspace_evaluation_plan.md": plan_path,
        "evaluator_day1.md": d1_path,
        "evaluator_day3.md": d3_path,
        "evaluator_day7.md": d7_path,
        "evaluation_sequence.csv": seq_path,
        "eval_dir": output_dir
    }
