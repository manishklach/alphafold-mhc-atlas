from __future__ import annotations

import json
from pathlib import Path

import yaml

from .demo_loader import describe_demo, list_all_demos, resolve_demo_project, resolve_demo_workspace
from .project_index import build_project_inventory
from .resource_paths import REPO_ROOT, RESOURCE_ROOT, repo_or_resource_path
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
        "packaging": validate_demo_packaging(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "demo_bundle_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_demo_packaging_manifest() -> dict[str, object]:
    manifest_path = repo_or_resource_path("data", "demo_packaging_manifest.yaml")
    if not manifest_path.exists():
        return {"package_demos": [], "repo_only_demos": [], "notes": {}}
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {"package_demos": [], "repo_only_demos": [], "notes": {}}


def validate_demo_packaging() -> dict[str, object]:
    manifest = load_demo_packaging_manifest()
    package_demos = sorted(str(name) for name in manifest.get("package_demos", []))
    repo_only_demos = sorted(str(name) for name in manifest.get("repo_only_demos", []))
    repo_demo_root = REPO_ROOT / "demo"
    resource_demo_root = RESOURCE_ROOT / "demo"
    repo_demo_names = sorted(path.name for path in repo_demo_root.iterdir() if path.is_dir()) if repo_demo_root.exists() else []
    resource_demo_names = sorted(path.name for path in resource_demo_root.iterdir() if path.is_dir()) if resource_demo_root.exists() else []

    missing_from_repo = sorted(name for name in package_demos + repo_only_demos if name not in repo_demo_names)
    missing_from_package = sorted(name for name in package_demos if name not in resource_demo_names)
    unexpected_packaged = sorted(name for name in resource_demo_names if name not in package_demos)
    unclassified_repo_demos = sorted(name for name in repo_demo_names if name not in package_demos and name not in repo_only_demos)

    return {
        "valid": not any([missing_from_repo, missing_from_package, unexpected_packaged, unclassified_repo_demos]),
        "package_demos": package_demos,
        "repo_only_demos": repo_only_demos,
        "repo_demo_names": repo_demo_names,
        "resource_demo_names": resource_demo_names,
        "missing_from_repo": missing_from_repo,
        "missing_from_package": missing_from_package,
        "unexpected_packaged": unexpected_packaged,
        "unclassified_repo_demos": unclassified_repo_demos,
    }
