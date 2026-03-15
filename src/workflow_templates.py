from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class WorkflowTemplate:
    name: str
    description: str
    recommended_scenarios: list[str]
    recommended_packet_types: list[str]
    recommended_role_views: list[str]
    checklist_focus: list[str]
    expected_outputs: list[str]
    cadence_label: str | None
    packet_template: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "recommended_scenarios": self.recommended_scenarios,
            "recommended_packet_types": self.recommended_packet_types,
            "recommended_role_views": self.recommended_role_views,
            "checklist_focus": self.checklist_focus,
            "expected_outputs": self.expected_outputs,
            "cadence_label": self.cadence_label,
            "packet_template": self.packet_template,
        }


def load_workflow_templates(path: Path | None = None) -> list[WorkflowTemplate]:
    template_path = path or repo_or_resource_path("data", "workflow_templates.yaml")
    if not template_path.exists():
        return []
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    raw_templates = payload.get("templates", []) if isinstance(payload, dict) else []
    templates: list[WorkflowTemplate] = []
    for entry in raw_templates:
        if not isinstance(entry, dict):
            continue
        templates.append(
            WorkflowTemplate(
                name=str(entry.get("name") or "").strip(),
                description=str(entry.get("description") or "").strip(),
                recommended_scenarios=_string_list(entry.get("recommended_scenarios")),
                recommended_packet_types=_string_list(entry.get("recommended_packet_types")),
                recommended_role_views=_string_list(entry.get("recommended_role_views")),
                checklist_focus=_string_list(entry.get("checklist_focus")),
                expected_outputs=_string_list(entry.get("expected_outputs")),
                cadence_label=_optional_string(entry.get("cadence_label")),
                packet_template=_optional_string(entry.get("packet_template")),
            )
        )
    return [template for template in templates if template.name]


def list_workflow_templates(path: Path | None = None) -> list[str]:
    return [template.name for template in load_workflow_templates(path)]


def get_workflow_template(name: str, path: Path | None = None) -> WorkflowTemplate:
    for template in load_workflow_templates(path):
        if template.name == name:
            return template
    raise KeyError(f"Unknown workflow template: {name}")


def _string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value not in {None, ""} else ""
    return text or None
