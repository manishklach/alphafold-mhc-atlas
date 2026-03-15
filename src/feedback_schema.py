from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


DEFAULT_CONCERN_TYPES = [
    "insufficient_evidence",
    "unclear_ranking",
    "biological_caveat",
    "missing_context",
    "scenario_needs_adjustment",
    "panel_needs_diversity_change",
    "export_needs_improvement",
    "ui_confusing",
    "data_quality_issue",
    "other",
]


@dataclass(frozen=True)
class FeedbackEntry:
    entity_type: str
    entity_id: str
    reviewer_name: str
    reviewer_role: str
    sentiment: str
    usefulness_rating: int | None
    clarity_rating: int | None
    confidence_in_output: str
    concern_type: str
    free_text_comment: str
    requested_followup: str
    status: str
    feedback_id: str = field(default_factory=lambda: f"fb_{uuid4().hex[:10]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
