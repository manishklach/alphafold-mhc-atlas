from __future__ import annotations

import json
from pathlib import Path

from .demo_loader import describe_demo, list_all_demos, resolve_demo_project, resolve_demo_workspace
from .project_index import build_project_inventory
from .workspace import load_workspace_config
from .workspace_index import build_workspace_inventory
from .version import __version__


def validate_demo(name: str) -> dict[str, object]:
    metadata = describe_demo(name)
    if metadata["has_project"]:
        project_dir = resolve_demo_project(name)
        inventory = build_project_inventory(project_dir)
        required = ["summary", "priority"]
        missing = [entry for entry in required if not inventory["tables"].get(entry, {}).get("exists")]
        return {
            "demo_name": name,
            "demo_type": "project",
            "project_dir": str(project_dir),
            "version": __version__,
            "valid": not missing,
            "missing_required_tables": missing,
            "available_modules": inventory["available_modules"],
            "has_walkthrough": metadata["has_walkthrough"],
        }
    if metadata["has_workspace"]:
        workspace_path = resolve_demo_workspace(name)
        workspace = load_workspace_config(workspace_path)
        inventory = build_workspace_inventory(workspace)
        missing_projects = [project["project_id"] for project in inventory["projects"] if project["project_status"] != "available"]
        return {
            "demo_name": name,
            "demo_type": "workspace",
            "workspace_path": str(workspace_path),
            "version": __version__,
            "valid": not missing_projects,
            "missing_projects": missing_projects,
            "num_projects": len(inventory["projects"]),
            "has_walkthrough": metadata["has_walkthrough"],
        }
    return {
        "demo_name": name,
        "demo_type": "docs_only",
        "version": __version__,
        "valid": metadata["has_walkthrough"] or Path(str(metadata["readme_path"])).exists(),
        "has_walkthrough": metadata["has_walkthrough"],
    }


def build_demo_bundle_manifest(output_dir: Path) -> Path:
    payload = {
        "version": __version__,
        "demos": [validate_demo(name) for name in list_all_demos()],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "demo_bundle_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
