from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .decision_history import build_decision_history
from .outcome_schema import OUTCOME_COLUMNS, load_outcome_schema, validate_outcome_frame
from .rationale_tracking import build_rationale_tracking
from .scope_text import brief_scope_markdown
from .workspace import WorkspaceConfig, load_workspace_config


def import_outcomes(workspace: WorkspaceConfig | str | Path, file_path: str | Path) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    source = Path(file_path).resolve()
    if source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        df = pd.DataFrame(payload if isinstance(payload, list) else payload.get("rows", []))
    else:
        df = pd.read_csv(source)
    df = validate_outcome_frame(df, load_outcome_schema())
    df = _fill_workspace_defaults(df, config)
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "outcomes_log.csv"
    existing = safe_read_csv(log_path)
    combined = pd.concat([existing, df], ignore_index=True) if not existing.empty else df
    combined = combined.drop_duplicates(subset=["outcome_id"], keep="last").reset_index(drop=True)
    combined = combined[OUTCOME_COLUMNS]
    combined.to_csv(log_path, index=False)
    return log_path


def summarize_outcomes(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "outcomes_log.csv"
    outcomes_df = safe_read_csv(log_path)
    if outcomes_df.empty:
        return _write_empty_outputs(output_dir, log_path)

    by_entity_df = (
        outcomes_df.groupby(["entity_type", "entity_id", "project_id", "outcome_class"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "entity_type", "entity_id"], ascending=[False, True, True])
    )
    summary_df = (
        outcomes_df.groupby(["outcome_class", "outcome_source", "confidence_in_outcome_context"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "outcome_class"], ascending=[False, True])
    )

    decision_outputs = build_decision_history(config)
    rationale_outputs = build_rationale_tracking(config)
    lineage_df = safe_read_csv(decision_outputs["decision_lineage.csv"])
    rationale_df = safe_read_csv(rationale_outputs["rationale_lineage.csv"])

    # Normalize entity types for merging: 'variant' in outcomes maps to 'shortlist_item' in decisions
    outcomes_for_merge = outcomes_df.copy()
    if "entity_type" in outcomes_for_merge.columns:
        outcomes_for_merge["entity_type"] = outcomes_for_merge["entity_type"].replace("variant", "shortlist_item")

    outcome_aware_df = lineage_df.merge(
        outcomes_for_merge[
            [
                "entity_type",
                "entity_id",
                "outcome_class",
                "outcome_source",
                "outcome_timestamp",
                "outcome_notes",
                "linked_artifacts",
            ]
        ],
        on=["entity_type", "entity_id"],
        how="left",
    )

    def _is_divergent(row: pd.Series) -> bool:
        status = str(row.get("current_status", "")).lower()
        outcome = str(row.get("outcome_class", "")).lower()
        if status == "rejected" and outcome in ["tested_followup", "wet_lab_supported", "wet_lab_not_supported"]:
            return True
        if status in ["shortlisted", "experimental_followup"] and outcome == "decision_reversed":
            return True
        return False

    outcome_aware_df["is_decision_outcome_divergent"] = outcome_aware_df.apply(_is_divergent, axis=1)

    followup_df = outcomes_df[
        outcomes_df["outcome_class"].isin(
            ["tested_followup", "wet_lab_supported", "wet_lab_not_supported", "pending_followup", "decision_reversed"]
        )
    ].copy()
    rationale_pattern_df = rationale_df.merge(
        outcomes_for_merge[["entity_type", "entity_id", "outcome_class", "outcome_source"]],
        on=["entity_type", "entity_id"],
        how="inner",
    )
    rationale_pattern_df = (
        rationale_pattern_df.groupby(["rationale_category", "outcome_class", "outcome_source"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "rationale_category"], ascending=[False, True])
    )

    paths = {
        "outcomes_log.csv": log_path,
        "outcomes_by_entity.csv": _write_df(output_dir / "outcomes_by_entity.csv", by_entity_df),
        "outcomes_summary.csv": _write_df(output_dir / "outcomes_summary.csv", summary_df),
        "outcome_aware_decision_summary.csv": _write_df(output_dir / "outcome_aware_decision_summary.csv", outcome_aware_df),
        "followup_pathways.csv": _write_df(output_dir / "followup_pathways.csv", followup_df),
        "rationale_to_outcome_patterns.csv": _write_df(output_dir / "rationale_to_outcome_patterns.csv", rationale_pattern_df),
    }
    outcome_digest = output_dir / "outcome_digest.md"
    outcome_digest.write_text(_build_outcome_digest(summary_df), encoding="utf-8")
    conservative_digest = output_dir / "conservative_learning_digest.md"
    conservative_digest.write_text(_build_learning_digest(followup_df, rationale_pattern_df), encoding="utf-8")
    paths["outcome_digest.md"] = outcome_digest
    paths["conservative_learning_digest.md"] = conservative_digest
    return paths


def _fill_workspace_defaults(df: pd.DataFrame, config: WorkspaceConfig) -> pd.DataFrame:
    working = df.copy()
    working["workspace_id"] = working.get("workspace_id", "").replace("", config.workspace_id) if "workspace_id" in working.columns else config.workspace_id
    for column in OUTCOME_COLUMNS:
        if column not in working.columns:
            working[column] = ""
    return working[OUTCOME_COLUMNS]


def _write_empty_outputs(output_dir: Path, log_path: Path) -> dict[str, Path]:
    outputs = {
        "outcomes_log.csv": _ensure_empty(log_path),
        "outcomes_by_entity.csv": _ensure_empty(output_dir / "outcomes_by_entity.csv"),
        "outcomes_summary.csv": _ensure_empty(output_dir / "outcomes_summary.csv"),
        "outcome_aware_decision_summary.csv": _ensure_empty(output_dir / "outcome_aware_decision_summary.csv"),
        "followup_pathways.csv": _ensure_empty(output_dir / "followup_pathways.csv"),
        "rationale_to_outcome_patterns.csv": _ensure_empty(output_dir / "rationale_to_outcome_patterns.csv"),
    }
    outcome_digest = output_dir / "outcome_digest.md"
    conservative_digest = output_dir / "conservative_learning_digest.md"
    outcome_digest.write_text(
        "# Outcome Digest\n\n- No outcomes have been imported.\n\nOutcomes are optional contextual evidence, not model truth.\n\n"
        + brief_scope_markdown(),
        encoding="utf-8",
    )
    conservative_digest.write_text(
        "# Conservative Learning Digest\n\n- No outcome-linked review learning summaries were available.\n\n"
        "Any future summaries remain descriptive and exploratory.\n\n"
        + brief_scope_markdown(),
        encoding="utf-8",
    )
    outputs["outcome_digest.md"] = outcome_digest
    outputs["conservative_learning_digest.md"] = conservative_digest
    return outputs


def _build_outcome_digest(summary_df: pd.DataFrame) -> str:
    lines = ["# Outcome Digest", ""]
    lines.append("Outcomes are tracked as downstream context. They are not used as biological ground truth for the structural workflow.")
    lines.append("")
    if summary_df.empty:
        lines.append("- No outcomes were available.")
    else:
        for row in summary_df.head(10).to_dict(orient="records"):
            confidence = row.get("confidence_in_outcome_context") or "unspecified"
            lines.append(
                f"- `{row['outcome_class']}` from `{row['outcome_source']}` at `{confidence}` outcome-context confidence: {row['count']} item(s)."
            )
    lines.extend(["", brief_scope_markdown()])
    return "\n".join(lines)


def _build_learning_digest(followup_df: pd.DataFrame, rationale_pattern_df: pd.DataFrame) -> str:
    lines = ["# Conservative Learning Digest", ""]
    lines.append("These summaries describe review follow-through and rationale patterns. They do not relabel the model as right or wrong.")
    lines.append("")
    if not followup_df.empty:
        lines.append(f"- Outcome-linked follow-up rows: {len(followup_df)}")
    else:
        lines.append("- No follow-up pathway rows were available.")
    if not rationale_pattern_df.empty:
        for row in rationale_pattern_df.head(10).to_dict(orient="records"):
            lines.append(
                f"- Rationale `{row['rationale_category']}` co-occurred with outcome `{row['outcome_class']}` from `{row['outcome_source']}` {row['count']} time(s)."
            )
    else:
        lines.append("- No rationale-to-outcome patterns were available.")
    lines.extend(["", brief_scope_markdown()])
    return "\n".join(lines)


def _write_df(path: Path, df: pd.DataFrame) -> Path:
    df.to_csv(path, index=False)
    return path


def _ensure_empty(path: Path) -> Path:
    pd.DataFrame().to_csv(path, index=False)
    return path
