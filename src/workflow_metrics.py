from __future__ import annotations

from datetime import datetime, timezone
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

    cycle_contexts = _review_cycle_contexts(config)
    cycle_rows: list[dict[str, object]] = []
    for cycle in cycle_contexts:
        summary = cycle["summary"]
        cycle_id = cycle["cycle_id"]
        shortlist_df = cycle["shortlist_df"]
        open_questions_df = cycle["open_questions_df"]
        next_actions_df = cycle["next_actions_df"]
        open_count = int(len(open_questions_df))
        next_count = int(len(next_actions_df))
        shortlist_count = int(len(shortlist_df))

        matching_outcomes = outcomes_df[
            outcomes_df["cycle_id"].astype(str) == cycle_id
        ] if not outcomes_df.empty and "cycle_id" in outcomes_df.columns else pd.DataFrame()
        shortlist_outcomes = _filter_outcomes_for_entities(
            matching_outcomes,
            shortlist_df,
            id_columns=["entity_id", "variant_id"],
            allowed_entity_types={"variant", "shortlist_item"},
        )
        question_outcomes = _filter_outcomes_for_entities(
            matching_outcomes,
            open_questions_df,
            id_columns=["question_id"],
            allowed_entity_types={"open_question", "question"},
        )
        closure_count = int(
            shortlist_outcomes["outcome_class"].isin(
                [
                    "tested_followup",
                    "deprioritized",
                    "wet_lab_supported",
                    "wet_lab_not_supported",
                    "archived_without_followup",
                ]
            ).sum()
        ) if not shortlist_outcomes.empty else 0
        resolved_questions = int(
            question_outcomes["outcome_class"].isin(
                ["tested_followup", "deprioritized", "archived_without_followup", "needs_more_context"]
            ).sum()
        ) if not question_outcomes.empty else 0
        completed_next_actions = int(
            next_actions_df["status"].astype(str).str.lower().isin(["done", "closed", "completed", "resolved", "archived"]).sum()
        ) if not next_actions_df.empty and "status" in next_actions_df.columns else 0
        cycle_rows.append(
            {
                "cycle_id": cycle_id,
                "template_name": summary.get("workflow_template") or "ad_hoc",
                "num_projects": int(summary.get("num_projects", len(config.projects)) or len(config.projects)),
                "unresolved_carryforward_ratio": round(float(open_count) / max(next_count, 1), 3),
                "shortlist_closure_ratio": round(float(closure_count) / max(shortlist_count, 1), 3),
                "next_action_completion_ratio": round(float(completed_next_actions) / max(next_count, 1), 3),
                "open_question_resolution_ratio": round(float(resolved_questions) / max(open_count, 1), 3) if open_count else 0.0,
                "promotion_to_followup_ratio": round(float(closure_count) / max(shortlist_count, 1), 3),
                "cycle_item_survival_rate": _cycle_survival_rate(multicycle_df, cycle_id),
                "cycle_status_churn_score": _cycle_status_churn(multicycle_df, cycle_id),
                "packet_to_handoff_conversion_count": _packet_to_handoff_count(config, cycle["generated_at"], cycle["next_generated_at"]),
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
                avg_cycle_status_churn=("cycle_status_churn_score", "mean"),
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
                "avg_cycle_status_churn",
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


def _cycle_status_churn(multicycle_df: pd.DataFrame, cycle_id: str) -> float:
    if multicycle_df.empty or "cycle_ids_serialized" not in multicycle_df.columns:
        return 0.0
    participating = multicycle_df["cycle_ids_serialized"].astype(str).str.contains(cycle_id, regex=False)
    if not participating.any() or "churn_score" not in multicycle_df.columns:
        return 0.0
    churn = pd.to_numeric(multicycle_df.loc[participating, "churn_score"], errors="coerce").fillna(0.0)
    return round(float(churn.mean()), 3)


def _packet_to_handoff_count(config: WorkspaceConfig, generated_at: datetime, next_generated_at: datetime | None) -> int:
    count = 0
    for project in config.projects:
        root = project.path / "handoff_bundles"
        if not root.exists():
            continue
        for item in root.iterdir():
            if not item.is_dir():
                continue
            modified_at = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
            if modified_at >= generated_at and (next_generated_at is None or modified_at < next_generated_at):
                count += 1
    return count


def _review_cycle_contexts(config: WorkspaceConfig) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    packet_root = config.output_dir / "review_packets"
    packet_dirs = sorted([item for item in packet_root.iterdir() if item.is_dir()], key=lambda item: item.name) if packet_root.exists() else []
    for index, packet_dir in enumerate(packet_dirs):
        summary = safe_read_json(packet_dir / "review_packet_summary.json")
        if not isinstance(summary, dict):
            summary = {}
        generated_at = _parse_generated_at(summary.get("generated_at"), packet_dir)
        next_generated_at = None
        if index + 1 < len(packet_dirs):
            next_summary = safe_read_json(packet_dirs[index + 1] / "review_packet_summary.json")
            if not isinstance(next_summary, dict):
                next_summary = {}
            next_generated_at = _parse_generated_at(next_summary.get("generated_at"), packet_dirs[index + 1])
        tables_dir = packet_dir / "review_packet_tables"
        contexts.append(
            {
                "cycle_id": packet_dir.name,
                "summary": summary,
                "generated_at": generated_at,
                "next_generated_at": next_generated_at,
                "shortlist_df": safe_read_csv(tables_dir / "shortlist.csv"),
                "open_questions_df": safe_read_csv(tables_dir / "open_questions.csv"),
                "next_actions_df": safe_read_csv(tables_dir / "next_action_table.csv"),
            }
        )
    return contexts


def _parse_generated_at(raw_value: object, fallback_dir: Path) -> datetime:
    if raw_value:
        try:
            return datetime.fromisoformat(str(raw_value).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback_dir.stat().st_mtime, tz=timezone.utc)


def _filter_outcomes_for_entities(
    outcomes_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    id_columns: list[str],
    allowed_entity_types: set[str],
) -> pd.DataFrame:
    if outcomes_df.empty or entities_df.empty or "entity_id" not in outcomes_df.columns:
        return pd.DataFrame()
    entity_ids: set[str] = set()
    for column in id_columns:
        if column in entities_df.columns:
            entity_ids.update(value for value in entities_df[column].astype(str).tolist() if value and value != "nan")
    if not entity_ids:
        return pd.DataFrame()
    filtered = outcomes_df[outcomes_df["entity_id"].astype(str).isin(entity_ids)].copy()
    if "entity_type" in filtered.columns:
        filtered = filtered[filtered["entity_type"].astype(str).isin(allowed_entity_types)]
    return filtered


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
