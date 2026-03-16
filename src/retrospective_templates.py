from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class RetrospectiveTemplate:
    template_id: str
    label: str
    description: str
    sections: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    role_views: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "label": self.label,
            "description": self.description,
            "sections": self.sections,
            "metrics": self.metrics,
            "role_views": self.role_views,
        }


def load_retrospective_templates(path: Path | None = None) -> list[RetrospectiveTemplate]:
    if path is None:
        path = repo_or_resource_path("data", "retrospective_templates.yaml")
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("templates", []) if isinstance(payload, dict) else []
    return [RetrospectiveTemplate(**t) for t in templates if isinstance(t, dict)]


def get_retrospective_template(template_id: str) -> RetrospectiveTemplate:
    templates = load_retrospective_templates()
    for t in templates:
        if t.template_id == template_id:
            return t
    raise ValueError(f"Retrospective template '{template_id}' not found.")
