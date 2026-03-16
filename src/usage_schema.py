from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class UsageEvent:
    event_id: str
    event_type: str
    workspace_id: str
    project_id: str | None = None
    cycle_id: str | None = None
    role_context: str | None = None
    surface: str | None = None
    artifact_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_usage_schema(path: Path | None = None) -> dict[str, list[dict[str, str]]]:
    path = path or repo_or_resource_path("data", "usage_event_schema.yaml")
    if not path.exists():
        return {"event_types": []}
    return yaml.safe_load(path.read_text(encoding="utf-8"))
