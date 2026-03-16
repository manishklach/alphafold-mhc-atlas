from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class JudgmentLabel:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class ReviewerJudgmentSchema:
    judgment_labels: list[JudgmentLabel]
    confidence_levels: list[str]
    rationale_categories: list[str]


def load_judgment_schema(path: Path | None = None) -> ReviewerJudgmentSchema:
    if path is None:
        path = repo_or_resource_path("data", "reviewer_judgment_schema.yaml")
    if not path.exists():
        return ReviewerJudgmentSchema([], [], [])
    
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    labels = [JudgmentLabel(**l) for l in payload.get("judgment_labels", [])]
    return ReviewerJudgmentSchema(
        judgment_labels=labels,
        confidence_levels=payload.get("confidence_levels", []),
        rationale_categories=payload.get("rationale_categories", [])
    )
