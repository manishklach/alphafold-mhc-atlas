from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json, safe_read_text
from .open_questions import build_open_questions
from .project_history import build_project_history
from .workspace import WorkspaceConfig, load_workspace_config


@dataclass(frozen=True)
class DecisionOccurrence:
    entity_type: str
    entity_id: str
    project_id: str
    workspace_id: str
    review_label: str
    generated_at: str
    status: str
    reason: str
    supporting_artifacts: str
    notes: str


def build_decision_history(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    lineage_rows: list[dict[str, object]] = []
    recurring_rows: list[dict[str, object]] = []
    carried_rows: list[dict[str, object]] = []
    resolved_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []
    diff_lines = ["# History Diff Summary", ""]

    for project in config.projects:
        if not project.path.exists():
            diff_lines.append(f"- `{project.project_id}` is missing and was skipped.")
            continue
        build_project_history(project.path)
        build_open_questions(project.path)
        occurrences = _collect_project_occurrences(project.path, project.project_id, config.workspace_id)
        grouped = _group_occurrences(occurrences)
        project_lineage, project_recurring, project_carried, project_resolved, project_unresolved = _build_lineage_tables(grouped)
        lineage_rows.extend(project_lineage)
        recurring_rows.extend(project_recurring)
        carried_rows.extend(project_carried)
        resolved_rows.extend(project_resolved)
        unresolved_rows.extend(project_unresolved)
        diff_lines.append(
            f"- `{project.project_id}`: {len(project_lineage)} lineage rows, {len(project_carried)} carried-forward items, {len(project_unresolved)} unresolved questions."
        )

    outputs = {
        "decision_lineage.csv": _write_table(memory_dir / "decision_lineage.csv", lineage_rows),
        "recurring_decisions.csv": _write_table(memory_dir / "recurring_decisions.csv", recurring_rows),
        "carried_forward_items.csv": _write_table(memory_dir / "carried_forward_items.csv", carried_rows),
        "resolved_questions.csv": _write_table(memory_dir / "resolved_questions.csv", resolved_rows),
        "unresolved_questions.csv": _write_table(memory_dir / "unresolved_questions.csv", unresolved_rows),
    }
    history_diff_path = memory_dir / "history_diff_summary.md"
    history_diff_path.write_text("\n".join(diff_lines), encoding="utf-8")
    outputs["history_diff_summary.md"] = history_diff_path
    return outputs


def _collect_project_occurrences(project_dir: Path, project_id: str, workspace_id: str) -> list[DecisionOccurrence]:
    occurrences: list[DecisionOccurrence] = []
    for cycle in _review_cycle_sources(project_dir):
        occurrences.extend(_load_cycle_occurrences(project_id, workspace_id, cycle["label"], cycle["generated_at"], cycle["root"], cycle["kind"]))
    current_generated = datetime.now(timezone.utc).isoformat()
    occurrences.extend(_load_current_occurrences(project_dir, project_id, workspace_id, current_generated))
    return occurrences


def _review_cycle_sources(project_dir: Path) -> list[dict[str, object]]:
    packet_root = project_dir / "review_packets"
    cycles: list[dict[str, object]] = []
    if not packet_root.exists():
        return cycles
    for path in sorted([item for item in packet_root.iterdir() if item.is_dir()], key=lambda item: item.name):
        summary = safe_read_json(path / "review_packet_summary.json")
        generated_at = str(summary.get("generated_at") or datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat())
        cycles.append({"label": path.name, "generated_at": generated_at, "root": path, "kind": "packet"})
    return cycles


def _load_cycle_occurrences(
    project_id: str,
    workspace_id: str,
    review_label: str,
    generated_at: str,
    cycle_root: Path,
    kind: str,
) -> list[DecisionOccurrence]:
    tables_root = cycle_root / "review_packet_tables"
    shortlist_df = safe_read_csv(tables_root / "shortlist.csv")
    open_questions_df = safe_read_csv(tables_root / "open_questions.csv")
    next_actions_df = safe_read_csv(tables_root / "next_action_table.csv")
    return _occurrences_from_tables(
        shortlist_df,
        open_questions_df,
        next_actions_df,
        project_id,
        workspace_id,
        review_label,
        generated_at,
        cycle_root,
        historical=True,
    )


def _load_current_occurrences(
    project_dir: Path,
    project_id: str,
    workspace_id: str,
    generated_at: str,
) -> list[DecisionOccurrence]:
    shortlist_df = safe_read_csv(project_dir / "review" / "shortlist.csv")
    open_questions_df = safe_read_csv(project_dir / "analysis" / "open_questions.csv")
    next_actions_df = safe_read_csv(project_dir / "analysis" / "next_action_table.csv")
    return _occurrences_from_tables(
        shortlist_df,
        open_questions_df,
        next_actions_df,
        project_id,
        workspace_id,
        "current",
        generated_at,
        project_dir,
        historical=False,
    )


def _occurrences_from_tables(
    shortlist_df: pd.DataFrame,
    open_questions_df: pd.DataFrame,
    next_actions_df: pd.DataFrame,
    project_id: str,
    workspace_id: str,
    review_label: str,
    generated_at: str,
    root: Path,
    historical: bool,
) -> list[DecisionOccurrence]:
    rows: list[DecisionOccurrence] = []
    for record in shortlist_df.to_dict(orient="records"):
        entity_id = str(record.get("entity_id") or record.get("variant_id") or "").strip()
        if not entity_id:
            continue
        rows.append(
            DecisionOccurrence(
                entity_type="shortlist_item",
                entity_id=entity_id,
                project_id=project_id,
                workspace_id=workspace_id,
                review_label=review_label,
                generated_at=generated_at,
                status=str(record.get("review_status") or "shortlisted"),
                reason=str(record.get("rationale") or record.get("selection_reason") or "").strip(),
                supporting_artifacts=str((root / ("review_packet_tables/shortlist.csv" if historical else "review/shortlist.csv")).as_posix()),
                notes=str(record.get("next_action") or "").strip(),
            )
        )
    for record in open_questions_df.to_dict(orient="records"):
        question_id = str(record.get("question_id") or "").strip()
        if not question_id:
            continue
        rows.append(
            DecisionOccurrence(
                entity_type="open_question",
                entity_id=question_id,
                project_id=project_id,
                workspace_id=workspace_id,
                review_label=review_label,
                generated_at=generated_at,
                status="open",
                reason=str(record.get("question_text") or "").strip(),
                supporting_artifacts=str((root / ("review_packet_tables/open_questions.csv" if historical else "analysis/open_questions.csv")).as_posix()),
                notes=str(record.get("notes") or "").strip(),
            )
        )
    for record in next_actions_df.to_dict(orient="records"):
        entity_id = str(record.get("entity_id") or "").strip()
        action_type = str(record.get("action_type") or "").strip()
        if not entity_id or not action_type:
            continue
        rows.append(
            DecisionOccurrence(
                entity_type="next_action",
                entity_id=f"{entity_id}:{action_type}",
                project_id=project_id,
                workspace_id=workspace_id,
                review_label=review_label,
                generated_at=generated_at,
                status=str(record.get("status") or "open"),
                reason=str(record.get("rationale") or "").strip(),
                supporting_artifacts=str((root / ("review_packet_tables/next_action_table.csv" if historical else "analysis/next_action_table.csv")).as_posix()),
                notes=str(record.get("owner_role_suggestion") or "").strip(),
            )
        )
    return rows


def _group_occurrences(occurrences: list[DecisionOccurrence]) -> dict[tuple[str, str, str, str], list[DecisionOccurrence]]:
    grouped: dict[tuple[str, str, str, str], list[DecisionOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(occurrence.entity_type, occurrence.entity_id, occurrence.project_id, occurrence.workspace_id)].append(occurrence)
    for key in grouped:
        grouped[key] = sorted(grouped[key], key=lambda item: (item.generated_at, item.review_label))
    return grouped


def _build_lineage_tables(grouped: dict[tuple[str, str, str, str], list[DecisionOccurrence]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    lineage_rows: list[dict[str, object]] = []
    recurring_rows: list[dict[str, object]] = []
    carried_rows: list[dict[str, object]] = []
    resolved_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []
    for (entity_type, entity_id, project_id, workspace_id), occurrences in grouped.items():
        first = occurrences[0]
        latest = occurrences[-1]
        prior = occurrences[-2] if len(occurrences) > 1 else None
        current_status = latest.status
        prior_status = prior.status if prior else ""
        decision_reason = latest.reason or prior_status or "No explicit rationale recorded."
        lineage = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "project_id": project_id,
            "workspace_id": workspace_id,
            "first_seen_review": first.review_label,
            "latest_seen_review": latest.review_label,
            "current_status": current_status,
            "prior_status": prior_status,
            "decision_reason_summary": decision_reason,
            "supporting_artifacts": ";".join(sorted({occ.supporting_artifacts for occ in occurrences if occ.supporting_artifacts})),
            "notes": latest.notes,
        }
        lineage_rows.append(lineage)
        if len(occurrences) > 1:
            recurring_rows.append({**lineage, "num_reviews_seen": len(occurrences)})
            carried_rows.append({**lineage, "carry_forward_reason": "Seen across multiple review cycles."})
        if entity_type == "open_question":
            if latest.review_label == "current":
                unresolved_rows.append({**lineage, "resolution_status": "unresolved"})
            else:
                resolved_rows.append({**lineage, "resolution_status": "resolved"})
    return lineage_rows, recurring_rows, carried_rows, resolved_rows, unresolved_rows


def _write_table(path: Path, rows: list[dict[str, object]]) -> Path:
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path
