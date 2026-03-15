from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WorkspaceProject:
    project_id: str
    path: Path
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        return payload


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace_id: str
    name: str
    description: str
    projects: list[WorkspaceProject]
    role_views_enabled: bool
    review_packets_enabled: bool
    decision_packets_enabled: bool
    output_dir: Path
    source_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "projects": [project.to_dict() for project in self.projects],
            "role_views_enabled": self.role_views_enabled,
            "review_packets_enabled": self.review_packets_enabled,
            "decision_packets_enabled": self.decision_packets_enabled,
            "output_dir": str(self.output_dir),
            "source_path": str(self.source_path),
        }


def load_workspace_config(path: str | Path) -> WorkspaceConfig:
    config_path = Path(path).resolve()
    payload = _load_workspace_payload(config_path)
    workspace = payload.get("workspace", payload)
    if not isinstance(workspace, dict):
        raise ValueError("Workspace config must deserialize to an object.")

    workspace_id = str(workspace.get("workspace_id") or config_path.stem).strip()
    if not workspace_id:
        raise ValueError("workspace.workspace_id must not be empty.")
    name = str(workspace.get("name") or workspace_id).strip()
    description = str(workspace.get("description") or "").strip()
    projects_raw = workspace.get("projects", [])
    if not isinstance(projects_raw, list) or not projects_raw:
        raise ValueError("workspace.projects must be a non-empty list.")

    projects: list[WorkspaceProject] = []
    for index, entry in enumerate(projects_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"workspace.projects[{index}] must be an object.")
        project_id = str(entry.get("id") or entry.get("project_id") or "").strip()
        if not project_id:
            raise ValueError(f"workspace.projects[{index}] must include id.")
        project_path = _resolve_path(config_path.parent, entry.get("path"))
        tags = [str(tag).strip() for tag in entry.get("tags", []) if str(tag).strip()]
        notes = str(entry.get("notes") or "").strip()
        projects.append(WorkspaceProject(project_id=project_id, path=project_path, tags=tags, notes=notes))

    output_dir_raw = workspace.get("output_dir") or str(config_path.parent / f"{workspace_id}_outputs")
    return WorkspaceConfig(
        workspace_id=workspace_id,
        name=name,
        description=description,
        projects=projects,
        role_views_enabled=bool(workspace.get("role_views", {}).get("enabled", True)),
        review_packets_enabled=bool(workspace.get("review_packets", {}).get("enabled", True)),
        decision_packets_enabled=bool(workspace.get("decision_packets", {}).get("enabled", True)),
        output_dir=_resolve_path(config_path.parent, output_dir_raw),
        source_path=config_path,
    )


def _load_workspace_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    elif suffix == ".json":
        payload = json.loads(text)
    else:
        raise ValueError(f"Unsupported workspace config extension: {path.suffix}")
    if not isinstance(payload, dict):
        raise ValueError("Workspace config must deserialize to an object.")
    return payload


def _resolve_path(base_dir: Path, value: Any) -> Path:
    if value in {None, ""}:
        raise ValueError("Workspace path values must not be empty.")
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path
