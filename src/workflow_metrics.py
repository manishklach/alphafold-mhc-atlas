from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json
from .multicycle_history import summarize_multicycle_history
from .outcomes import summarize_outcomes
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_workflow_metrics(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    multicycle_outputs = summarize_multicycle_history(config)
    outcomes_outputs = summarize_outcomes(config)
    multicycle_df = safe_read_csv(multicycle_outputs["multicycle_decision_summary.csv"])
    outcomes_df = safe_read_csv(outcomes_outputs["outcomes_log.csv"])

    cycle_rows: list[dict[str, object]] = []
    packet_root = config.output_dir / "review_packets"
    for packet_dir in sorted([item for item in packet_root.iterdir() if item.is_dir()], key=lambda item: item.name) if packet_root.exists() else []:
        summary = safe_read_json(packet_dir / "review_packet_summary.json")
        if not isinstance(summary, dict):
            summary = {}
        cycle_id = packet_dir.name
        open_count = int(summary.get("num_open_questions", 0) or 0)
        next_count = int(summary.get("num_next_actions", 0) or 0)
        shortlist_count = int(summary.get("num_shortlist_items", 0) or 0)
        matching_outcomes = outcomes_df[outcomes_df["cycle_id"].astype(str) == cycle_id] if not outcomes_df.empty and "cycle_id" in outcomes_df.columns else pd.DataFrame()
        closure_count = int(
            matching_outcomes["outcome_class"].isin(
                [
                    "tested_followup",
                    "deprioritized",
                    "wet_lab_supported",
                    "wet_lab_not_supported",
                    "archived_without_followup",
                ]
            ).sum()
        ) if not matching_outcomes.empty else 0
        resolved_questions = int(
            matching_outcomes["outcome_class"].isin(["tested_followup", "deprioritized", "archived_without_followup"]).sum()
        ) if not matching_outcomes.empty else 0
        cycle_rows.append(
            {
                "cycle_id": cycle_id,
                "template_name": summary.get("workflow_template") or "ad_hoc",
                "num_projects": int(summary.get("num_projects", len(config.projects)) or len(config.projects)),
                "unresolved_carryforward_ratio": round(float(open_count) / max(next_count, 1), 3),
                "shortlist_closure_ratio": round(float(closure_count) / max(shortlist_count, 1), 3),
                "next_action_completion_ratio": round(float(closure_count) / max(next_count, 1), 3),
                "open_question_resolution_ratio": round(float(resolved_questions) / max(open_count, 1), 3) if open_count else 0.0,
                "promotion_to_followup_ratio": round(float(closure_count) / max(shortlist_count, 1), 3),
                "cycle_item_survival_rate": _cycle_survival_rate(multicycle_df, cycle_id),
                "packet_to_handoff_conversion_count": _packet_to_handoff_count(config),
            }
        )

    cycle_df = pd.DataFrame(cycle_rows)
    workflow_df = (
        cycle_df.groupby("template_name", dropna=False)
        .agg(
            avg_unresolved_carryforward=("unresolved_carryforward_ratio", "mean"),
            avg_shortlist_closure=("shortlist_closure_ratio", "mean"),
            avg_next_action_completion=("next_action_completion_ratio", "mean"),
            avg_open_question_resolution=("open_question_resolution_ratio", "mean"),
            avg_promotion_to_followup=("promotion_to_followup_ratio", "mean"),
            avg_cycle_item_survival_rate=("cycle_item_survival_rate", "mean"),
            num_cycles=("cycle_id", "count"),
        )
        .reset_index()
        if not cycle_df.empty
        else pd.DataFrame(
            columns=[
                "template_name",
                "avg_unresolved_carryforward",
                "avg_shortlist_closure",
                "avg_next_action_completion",
                "avg_open_question_resolution",
                "avg_promotion_to_followup",
                "avg_cycle_item_survival_rate",
                "num_cycles",
            ]
        )
    )
    closure_path = output_dir / "closure_summary.md"
    closure_path.write_text(_build_closure_summary(workflow_df), encoding="utf-8")
    return {
        "workflow_metrics.csv": _write_df(output_dir / "workflow_metrics.csv", workflow_df),
        "cycle_operational_metrics.csv": _write_df(output_dir / "cycle_operational_metrics.csv", cycle_df),
        "closure_summary.md": closure_path,
    }


def _cycle_survival_rate(multicycle_df: pd.DataFrame, cycle_id: str) -> float:
    if multicycle_df.empty or "cycle_ids_serialized" not in multicycle_df.columns:
        return 0.0
    participating = multicycle_df["cycle_ids_serialized"].astype(str).str.contains(cycle_id, regex=False)
    if not participating.any():
        return 0.0
    carried = pd.to_numeric(multicycle_df.loc[participating, "carry_forward_count"], errors="coerce").fillna(0)
    return round(float((carried > 0).sum()) / max(len(carried), 1), 3)


def _packet_to_handoff_count(config: WorkspaceConfig) -> int:
    count = 0
    for project in config.projects:
        root = project.path / "handoff_bundles"
        if root.exists() and any(item.is_dir() for item in root.iterdir()):
            count += 1
    return count


def _build_closure_summary(workflow_df: pd.DataFrame) -> str:
    lines = ["# Closure Summary", ""]
    lines.append("These are operational workflow metrics, not scientific validation metrics.")
    lines.append("")
    if workflow_df.empty:
        lines.append("- No cycle metrics were available.")
    else:
        for row in workflow_df.to_dict(orient="records"):
            lines.append(
                f"- Template `{row['template_name']}` was associated with average unresolved carry-forward "
                f"{row['avg_unresolved_carryforward']:.2f} across {int(row['num_cycles'])} cycle(s)."
            )
    return "\n".join(lines)


def _write_df(path: Path, df: pd.DataFrame) -> Path:
    df.to_csv(path, index=False)
    return path
