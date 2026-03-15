from __future__ import annotations

import json
from pathlib import Path

from .demo_loader import list_demo_projects, resolve_demo_project
from .project_index import build_project_inventory
from .version import __version__


def validate_demo(name: str) -> dict[str, object]:
    project_dir = resolve_demo_project(name)
    inventory = build_project_inventory(project_dir)
    required = ["summary", "priority"]
    missing = [entry for entry in required if not inventory["tables"].get(entry, {}).get("exists")]
    return {
        "demo_name": name,
        "project_dir": str(project_dir),
        "version": __version__,
        "valid": not missing,
        "missing_required_tables": missing,
        "available_modules": inventory["available_modules"],
    }


def build_demo_bundle_manifest(output_dir: Path) -> Path:
    payload = {
        "version": __version__,
        "demos": [validate_demo(name) for name in list_demo_projects()],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "demo_bundle_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
