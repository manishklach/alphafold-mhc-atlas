from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .scope_text import brief_scope_markdown
from .workflow_metrics import summarize_workflow_metrics
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_template_effectiveness(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_outputs = summarize_workflow_metrics(config)
    cycle_df = safe_read_csv(Path(metric_outputs["cycle_operational_metrics.csv"]))
    if cycle_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "template_name",
                "num_cycles_used",
                "num_projects_used",
                "avg_unresolved_carryforward",
                "avg_churn_score",
                "avg_open_questions_resolved",
                "avg_next_action_closure_rate",
                "effectiveness_notes",
                "data_quality_notes",
            ]
        )
        unresolved_df = pd.DataFrame(columns=["template_name", "cycle_id", "unresolved_carryforward_ratio"])
    else:
        cycle_df = cycle_df.copy()
        cycle_df["avg_churn_score"] = cycle_df.get("cycle_item_survival_rate", 0.0).apply(lambda value: round(1.0 - float(value), 3))
        summary_df = (
            cycle_df.groupby("template_name", dropna=False)
            .agg(
                num_cycles_used=("cycle_id", "count"),
                avg_unresolved_carryforward=("unresolved_carryforward_ratio", "mean"),
                avg_churn_score=("avg_churn_score", "mean"),
                avg_open_questions_resolved=("open_question_resolution_ratio", "mean"),
                avg_next_action_closure_rate=("next_action_completion_ratio", "mean"),
            )
            .reset_index()
        )
        summary_df["num_projects_used"] = len(config.projects)
        summary_df["effectiveness_notes"] = (
            "Associational operational summary only; lower unresolved carry-forward does not prove better biology."
        )
        summary_df["data_quality_notes"] = "Partial timestamps, sparse outcomes, and missing review artifacts are handled conservatively."
        unresolved_df = cycle_df[["template_name", "cycle_id", "unresolved_carryforward_ratio"]].copy()

    digest_path = output_dir / "workflow_effectiveness_digest.md"
    digest_path.write_text(_build_digest(summary_df), encoding="utf-8")
    by_cycle_path = output_dir / "template_effectiveness_by_cycle.csv"
    cycle_df.to_csv(by_cycle_path, index=False)
    summary_path = output_dir / "template_effectiveness_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    unresolved_path = output_dir / "unresolved_carryforward_by_template.csv"
    unresolved_df.to_csv(unresolved_path, index=False)
    return {
        "template_effectiveness_summary.csv": summary_path,
        "template_effectiveness_by_cycle.csv": by_cycle_path,
        "unresolved_carryforward_by_template.csv": unresolved_path,
        "workflow_effectiveness_digest.md": digest_path,
    }


def _build_digest(summary_df: pd.DataFrame) -> str:
    lines = ["# Workflow Effectiveness Digest", ""]
    lines.append("These summaries describe workflow-operational associations. They are not causal proof and not scientific validation.")
    lines.append("")
    if summary_df.empty:
        lines.append("- No workflow-template effectiveness data was available.")
    else:
        for row in summary_df.to_dict(orient="records"):
            lines.append(
                f"- Template `{row['template_name']}` was associated with average unresolved carry-forward "
                f"{row['avg_unresolved_carryforward']:.2f} and average next-action closure "
                f"{row['avg_next_action_closure_rate']:.2f} across {int(row['num_cycles_used'])} cycle(s)."
            )
    lines.extend(["", brief_scope_markdown()])
    return "\n".join(lines)
