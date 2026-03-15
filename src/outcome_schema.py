from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class OutcomeSchema:
    allowed_outcome_classes: list[str]
    allowed_confidence_levels: list[str]
    required_columns: list[str]


OUTCOME_COLUMNS = [
    "outcome_id",
    "entity_type",
    "entity_id",
    "project_id",
    "workspace_id",
    "cycle_id",
    "outcome_class",
    "outcome_source",
    "outcome_timestamp",
    "outcome_notes",
    "linked_artifacts",
    "reviewer_or_owner",
    "confidence_in_outcome_context",
    "not_model_truth_flag",
]


def load_outcome_schema(path: Path | None = None) -> OutcomeSchema:
    schema_path = path or repo_or_resource_path("data", "outcome_schema.yaml")
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {}
    if not isinstance(payload, dict):
        payload = {}
    return OutcomeSchema(
        allowed_outcome_classes=[str(value) for value in payload.get("allowed_outcome_classes", [])],
        allowed_confidence_levels=[str(value) for value in payload.get("allowed_confidence_in_outcome_context", [])],
        required_columns=[str(value) for value in payload.get("required_columns", [])],
    )


def validate_outcome_frame(df: pd.DataFrame, schema: OutcomeSchema | None = None) -> pd.DataFrame:
    schema = schema or load_outcome_schema()
    missing_required = [column for column in schema.required_columns if column not in df.columns]
    if missing_required:
        raise ValueError(f"Outcome input is missing required columns: {missing_required}")

    working = df.copy()
    for column in OUTCOME_COLUMNS:
        if column not in working.columns:
            working[column] = ""
    working = working[OUTCOME_COLUMNS]
    for column in OUTCOME_COLUMNS:
        working[column] = working[column].fillna("").astype(str).str.strip()

    invalid_classes = sorted(set(working["outcome_class"]) - set(schema.allowed_outcome_classes))
    if invalid_classes:
        raise ValueError(f"Outcome input contains unsupported outcome_class values: {invalid_classes}")
    invalid_confidence = sorted(set(working["confidence_in_outcome_context"]) - set(schema.allowed_confidence_levels) - {""})
    if invalid_confidence:
        raise ValueError(
            "Outcome input contains unsupported confidence_in_outcome_context values: "
            f"{invalid_confidence}"
        )
    invalid_flags = sorted(
        value for value in set(working["not_model_truth_flag"].str.lower()) if value not in {"true", "false", ""}
    )
    if invalid_flags:
        raise ValueError(f"Outcome input contains unsupported not_model_truth_flag values: {invalid_flags}")

    working["not_model_truth_flag"] = working["not_model_truth_flag"].str.lower().replace({"": "true"})
    if (working["not_model_truth_flag"] != "true").any():
        raise ValueError("Outcome rows must keep not_model_truth_flag=true to avoid implying model truth.")
    return working
