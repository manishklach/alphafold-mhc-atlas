from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class ExecutionTemplate:
    template_id: str
    label: str
    description: str
    default_task_types: list[str] = field(default_factory=list)
    default_role_suggestions: dict[str, str] = field(default_factory=dict)
    default_checklist: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "label": self.label,
            "description": self.description,
            "default_task_types": self.default_task_types,
            "default_role_suggestions": self.default_role_suggestions,
            "default_checklist": self.default_checklist,
        }


def load_execution_templates(path: Path | None = None) -> list[ExecutionTemplate]:
    if path is None:
        path = repo_or_resource_path("data", "execution_templates.yaml")
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("templates", []) if isinstance(payload, dict) else []
    return [ExecutionTemplate(**t) for t in templates if isinstance(t, dict)]


def get_execution_template(template_id: str) -> ExecutionTemplate:
    templates = load_execution_templates()
    for t in templates:
        if t.template_id == template_id:
            return t
    raise ValueError(f"Execution template '{template_id}' not found.")
