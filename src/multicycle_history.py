from __future__ import annotations

from pathlib import Path

import pandas as pd

from .decision_history import _collect_project_occurrences, _group_occurrences
from .scope_text import brief_scope_markdown
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_multicycle_history(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    churn_rows: list[dict[str, object]] = []
    stable_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for project in config.projects:
        if not project.path.exists():
            continue
        grouped = _group_occurrences(_collect_project_occurrences(project.path, project.project_id, config.workspace_id))
        for (entity_type, entity_id, project_id, workspace_id), occurrences in grouped.items():
            cycle_ids = [str(item.review_label) for item in occurrences]
            statuses = [str(item.status) for item in occurrences]
            unique_cycle_ids = _dedupe_preserve(cycle_ids)
            shortlist_count = sum(1 for item in occurrences if item.entity_type == "shortlist_item")
            unresolved_count = sum(1 for item in occurrences if item.entity_type == "open_question")
            carry_forward_count = max(len(unique_cycle_ids) - 1, 0)
            churn_score = _compute_churn_score(statuses)
            latest = occurrences[-1]
            row = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "project_id": project_id,
                "workspace_id": workspace_id,
                "num_cycles_seen": len(unique_cycle_ids),
                "cycle_ids_serialized": ";".join(unique_cycle_ids),
                "status_path_serialized": ";".join(statuses),
                "shortlist_count": shortlist_count,
                "carry_forward_count": carry_forward_count,
                "unresolved_count": unresolved_count,
                "churn_score": churn_score,
                "latest_status": latest.status,
                "notes": _build_notes(entity_type, unique_cycle_ids, churn_score, unresolved_count),
            }
            rows.append(row)
            if churn_score > 0:
                churn_rows.append(row)
            if entity_type == "shortlist_item" and len(unique_cycle_ids) >= 2 and churn_score == 0:
                stable_rows.append(row)
            if entity_type == "open_question" and len(unique_cycle_ids) >= 2:
                unresolved_rows.append(row)

    summary_df = pd.DataFrame(rows).sort_values(
        ["num_cycles_seen", "carry_forward_count", "entity_type", "entity_id"],
        ascending=[False, False, True, True],
    ) if rows else _empty_summary()
    churn_df = pd.DataFrame(churn_rows).sort_values(
        ["churn_score", "num_cycles_seen", "entity_id"],
        ascending=[False, False, True],
    ) if churn_rows else summary_df.iloc[0:0].copy()
    stable_df = pd.DataFrame(stable_rows).sort_values(
        ["num_cycles_seen", "entity_id"],
        ascending=[False, True],
    ) if stable_rows else summary_df.iloc[0:0].copy()
    unresolved_multi_df = pd.DataFrame(unresolved_rows).sort_values(
        ["num_cycles_seen", "entity_id"],
        ascending=[False, True],
    ) if unresolved_rows else summary_df.iloc[0:0].copy()

    digest_path = output_dir / "multicycle_change_digest.md"
    digest_path.write_text(_build_digest(summary_df, stable_df, unresolved_multi_df, churn_df), encoding="utf-8")
    return {
        "multicycle_decision_summary.csv": _write_df(output_dir / "multicycle_decision_summary.csv", summary_df),
        "decision_churn.csv": _write_df(output_dir / "decision_churn.csv", churn_df),
        "stable_shortlist_items.csv": _write_df(output_dir / "stable_shortlist_items.csv", stable_df),
        "repeatedly_unresolved_items.csv": _write_df(output_dir / "repeatedly_unresolved_items.csv", unresolved_multi_df),
        "multicycle_change_digest.md": digest_path,
    }


def _compute_churn_score(statuses: list[str]) -> float:
    if len(statuses) < 2:
        return 0.0
    transitions = 0
    for previous, current in zip(statuses, statuses[1:]):
        if previous != current:
            transitions += 1
    return round(transitions / max(len(statuses) - 1, 1), 3)


def _dedupe_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _build_notes(entity_type: str, cycle_ids: list[str], churn_score: float, unresolved_count: int) -> str:
    if len(cycle_ids) <= 1:
        return "Only one review cycle was available."
    if entity_type == "open_question" and unresolved_count >= 2:
        return "Repeatedly unresolved across multiple cycles."
    if churn_score == 0:
        return "Stable across observed review cycles."
    return "Exploratory multi-cycle pattern with status changes."


def _build_digest(
    summary_df: pd.DataFrame,
    stable_df: pd.DataFrame,
    unresolved_df: pd.DataFrame,
    churn_df: pd.DataFrame,
) -> str:
    lines = ["# Multi-Cycle Change Digest", ""]
    lines.append("These patterns describe review continuity over time. They do not convert review history into biological validation.")
    lines.append("")
    if summary_df.empty:
        lines.append("- Fewer than two meaningful review cycles were available.")
    else:
        lines.append(f"- Tracked items across cycles: {len(summary_df)}")
        lines.append(f"- Stable shortlist items: {len(stable_df)}")
        lines.append(f"- Repeatedly unresolved questions: {len(unresolved_df)}")
        lines.append(f"- Churny items with status changes: {len(churn_df)}")
        if not stable_df.empty:
            lines.append(f"- Example stable shortlist items: {', '.join(stable_df.head(3)['entity_id'].astype(str).tolist())}")
        if not churn_df.empty:
            lines.append(f"- Example churny items: {', '.join(churn_df.head(3)['entity_id'].astype(str).tolist())}")
    lines.extend(["", brief_scope_markdown()])
    return "\n".join(lines)


def _empty_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "entity_type",
            "entity_id",
            "project_id",
            "workspace_id",
            "num_cycles_seen",
            "cycle_ids_serialized",
            "status_path_serialized",
            "shortlist_count",
            "carry_forward_count",
            "unresolved_count",
            "churn_score",
            "latest_status",
            "notes",
        ]
    )


def _write_df(path: Path, df: pd.DataFrame) -> Path:
    df.to_csv(path, index=False)
    return path
