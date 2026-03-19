from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from .data_access import safe_read_csv
from .resource_paths import repo_or_resource_path
from .workspace import WorkspaceConfig, load_workspace_config


def build_rationale_tracking(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    categories = _load_rationale_categories()
    for project in config.projects:
        if not project.path.exists():
            continue
        prior_status_by_entity: dict[str, str] = {}
        prior_rationale_by_entity: dict[str, str] = {}
        prior_cycle_by_entity: dict[str, str] = {}
        for cycle_id, shortlist_df in _iter_shortlist_cycles(project.path):
            for record in shortlist_df.to_dict(orient="records"):
                entity_id = str(record.get("entity_id") or record.get("variant_id") or "").strip()
                if not entity_id:
                    continue
                val = record.get("rationale") or record.get("selection_reason") or ""
                rationale_text = str(val).strip() if not pd.isna(val) else ""
                status_val = record.get("review_status") or "shortlisted"
                decision_status = str(status_val).strip() if not pd.isna(status_val) else "shortlisted"
                rows.append(
                    {
                        "entity_type": "shortlist_item",
                        "entity_id": entity_id,
                        "project_id": project.project_id,
                        "workspace_id": config.workspace_id,
                        "cycle_id": cycle_id,
                        "prior_cycle_id": prior_cycle_by_entity.get(entity_id, ""),
                        "decision_status": decision_status,
                        "rationale_text": rationale_text,
                        "rationale_category": _categorize_rationale(rationale_text, categories),
                        "rationale_completeness": bool(rationale_text),
                        "rationale_length": len(rationale_text.split()),
                        "is_thin_rationale": bool(rationale_text and len(rationale_text.split()) < 3),
                        "is_silent_status_change": bool(
                            entity_id in prior_rationale_by_entity
                            and prior_status_by_entity[entity_id] != decision_status
                            and prior_rationale_by_entity[entity_id] == rationale_text
                        ),
                        "carry_forward_reason": str(record.get("next_action") or "").strip(),
                        "changed_from_prior_flag": bool(
                            entity_id in prior_rationale_by_entity
                            and prior_rationale_by_entity[entity_id] != rationale_text
                        ),
                        "notes": _build_notes(prior_status_by_entity.get(entity_id, ""), decision_status),
                    }
                )
                prior_status_by_entity[entity_id] = decision_status
                prior_rationale_by_entity[entity_id] = rationale_text
                prior_cycle_by_entity[entity_id] = cycle_id

    lineage_df = pd.DataFrame(rows)
    if lineage_df.empty:
        empty_lineage = _write_df(
            output_dir / "rationale_lineage.csv",
            pd.DataFrame(
                columns=[
                    "entity_type",
                    "entity_id",
                    "project_id",
                    "workspace_id",
                    "cycle_id",
                    "prior_cycle_id",
                    "decision_status",
                    "rationale_text",
                    "rationale_category",
                    "rationale_completeness",
                    "rationale_length",
                    "is_thin_rationale",
                    "is_silent_status_change",
                    "carry_forward_reason",
                    "changed_from_prior_flag",
                    "notes",
                ]
            ),
        )
        return {
            "rationale_lineage.csv": empty_lineage,
            "rationale_change_log.csv": _write_df(output_dir / "rationale_change_log.csv", pd.DataFrame()),
            "promotion_reasons_summary.csv": _write_df(output_dir / "promotion_reasons_summary.csv", pd.DataFrame()),
            "drop_reasons_summary.csv": _write_df(output_dir / "drop_reasons_summary.csv", pd.DataFrame()),
        }

    lineage_df = lineage_df.sort_values(["project_id", "entity_id", "cycle_id"]).reset_index(drop=True)
    change_df = lineage_df[lineage_df["changed_from_prior_flag"]].copy()
    promotion_df = (
        lineage_df[lineage_df["decision_status"].isin(["shortlisted", "experimental_followup", "report_inclusion"])]
        .groupby(["rationale_category"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "rationale_category"], ascending=[False, True])
    )
    drop_df = (
        lineage_df[lineage_df["decision_status"].isin(["rejected", "uncertain", "request_more_evidence"])]
        .groupby(["rationale_category"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "rationale_category"], ascending=[False, True])
    )
    return {
        "rationale_lineage.csv": _write_df(output_dir / "rationale_lineage.csv", lineage_df),
        "rationale_change_log.csv": _write_df(output_dir / "rationale_change_log.csv", change_df),
        "promotion_reasons_summary.csv": _write_df(output_dir / "promotion_reasons_summary.csv", promotion_df),
        "drop_reasons_summary.csv": _write_df(output_dir / "drop_reasons_summary.csv", drop_df),
    }


def _iter_shortlist_cycles(project_dir: Path) -> list[tuple[str, pd.DataFrame]]:
    cycles: list[tuple[str, pd.DataFrame]] = []
    packet_root = project_dir / "review_packets"
    if packet_root.exists():
        for packet_dir in sorted([item for item in packet_root.iterdir() if item.is_dir()], key=lambda item: item.name):
            cycles.append((packet_dir.name, safe_read_csv(packet_dir / "review_packet_tables" / "shortlist.csv")))
    cycles.append(("current", safe_read_csv(project_dir / "review" / "shortlist.csv")))
    return cycles


def _load_rationale_categories() -> dict[str, list[str]]:
    path = repo_or_resource_path("data", "rationale_categories.yaml")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    categories = payload.get("categories", {}) if isinstance(payload, dict) else {}
    return {
        str(name): [str(keyword).lower() for keyword in entry.get("keywords", [])]
        for name, entry in categories.items()
        if isinstance(entry, dict)
    }


def _categorize_rationale(text: str, categories: dict[str, list[str]]) -> str:
    lowered = text.lower()
    for category, keywords in categories.items():
        if any(keyword in lowered for keyword in keywords if keyword):
            return category
    return "other"


def _build_notes(prior_status: str, current_status: str) -> str:
    if not prior_status:
        return "Initial rationale record."
    if prior_status != current_status:
        return f"Decision status changed from `{prior_status}` to `{current_status}`."
    return "Decision status carried forward with updated or repeated rationale."


def _write_df(path: Path, df: pd.DataFrame) -> Path:
    df.to_csv(path, index=False)
    return path
