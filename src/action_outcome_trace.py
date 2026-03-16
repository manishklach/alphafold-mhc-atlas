from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_action_outcome_trace(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    # Load tasks across all plans
    plans_dir = config.output_dir / "execution_plans"
    tasks_dfs = []
    if plans_dir.exists():
        for plan_dir in plans_dir.iterdir():
            if plan_dir.is_dir():
                tasks_path = plan_dir / "followup_tasks.csv"
                if tasks_path.exists():
                    tasks_dfs.append(safe_read_csv(tasks_path))
                    
    if tasks_dfs:
        all_tasks_df = pd.concat(tasks_dfs, ignore_index=True)
    else:
        all_tasks_df = pd.DataFrame(columns=[
            "task_id", "plan_id", "project_id", "workspace_id", "entity_type", "entity_id",
            "task_type", "task_title", "status", "source_cycle_id"
        ])

    # Load outcomes
    outcomes_df = safe_read_csv(memory_dir / "outcomes_log.csv")
    if outcomes_df.empty:
        outcomes_df = pd.DataFrame(columns=["outcome_id", "entity_type", "entity_id", "outcome_class", "outcome_notes"])
        
    outcomes_for_merge = outcomes_df.copy()
    if "entity_type" in outcomes_for_merge.columns:
        outcomes_for_merge["entity_type"] = outcomes_for_merge["entity_type"].replace("variant", "shortlist_item")

    # Merge Tasks and Outcomes
    if not all_tasks_df.empty:
        trace_df = all_tasks_df.merge(
            outcomes_for_merge[["outcome_id", "entity_type", "entity_id", "outcome_class", "outcome_notes"]],
            on=["entity_type", "entity_id"],
            how="left"
        )
    else:
        trace_df = pd.DataFrame(columns=[
            "task_id", "plan_id", "project_id", "workspace_id", "entity_type", "entity_id",
            "task_type", "task_title", "status", "source_cycle_id", "outcome_id", "outcome_class", "outcome_notes"
        ])

    trace_df["trace_id"] = trace_df.apply(lambda row: f"trace_{row.get('task_id', 'unknown')}", axis=1)
    trace_df["not_model_truth_flag"] = True

    trace_path = memory_dir / "action_outcome_trace.csv"
    trace_df.to_csv(trace_path, index=False)

    summary_df = trace_df.groupby(["task_type", "status", "outcome_class"], dropna=False).size().reset_index(name="count")
    summary_path = memory_dir / "execution_to_outcome_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    md_path = memory_dir / "followup_path_trace.md"
    lines = [
        "# Action-to-Outcome Trace",
        "Traces items from execution task to recorded downstream outcome.",
        "",
        "## Important Caveat",
        "These traces link operational actions to context. They do not imply that task completion or outcome capture 'proves' the underlying model structure is biologically correct.",
        "",
        f"- Total Tasks: {len(all_tasks_df)}",
        f"- Tasks with Outcomes: {len(trace_df[trace_df['outcome_id'].notna()])}",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "action_outcome_trace.csv": trace_path,
        "execution_to_outcome_summary.csv": summary_path,
        "followup_path_trace.md": md_path
    }
