from __future__ import annotations

import json
from pathlib import Path

from .resource_paths import repo_or_resource_path

DEMO_ROOT = repo_or_resource_path("demo")


def list_all_demos() -> list[str]:
    if not DEMO_ROOT.exists():
        return []
    demos: list[str] = []
    for path in DEMO_ROOT.iterdir():
        if not path.is_dir():
            continue
        if (path / "project").exists() or (path / "workspace.yaml").exists() or (path / "README.md").exists():
            demos.append(path.name)
    return sorted(demos)


def list_demo_projects() -> list[str]:
    if not DEMO_ROOT.exists():
        return []
    return sorted(path.name for path in DEMO_ROOT.iterdir() if path.is_dir() and (path / "project").exists())


def resolve_demo_project(name: str) -> Path:
    project_dir = DEMO_ROOT / name / "project"
    if not project_dir.exists():
        raise FileNotFoundError(f"Demo project not found: {name}")
    return project_dir


def load_demo_readme(name: str) -> str:
    readme_path = DEMO_ROOT / name / "README.md"
    if not readme_path.exists():
        return ""
    return readme_path.read_text(encoding="utf-8", errors="replace")


def load_demo_walkthrough(name: str) -> str:
    walkthrough_path = DEMO_ROOT / name / "WALKTHROUGH.md"
    if not walkthrough_path.exists():
        return ""
    return walkthrough_path.read_text(encoding="utf-8", errors="replace")


def resolve_demo_workspace(name: str) -> Path:
    workspace_path = DEMO_ROOT / name / "workspace.yaml"
    if workspace_path.exists():
        return workspace_path
    raise FileNotFoundError(f"Demo workspace not found: {name}")


def describe_demo(name: str) -> dict[str, object]:
    demo_dir = DEMO_ROOT / name
    metadata_path = demo_dir / "demo.json"
    if metadata_path.exists():
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        payload = {}
    payload.setdefault("demo_name", name)
    payload.setdefault("has_project", (demo_dir / "project").exists())
    payload.setdefault("has_workspace", (demo_dir / "workspace.yaml").exists())
    payload.setdefault("has_walkthrough", (demo_dir / "WALKTHROUGH.md").exists())
    payload.setdefault("readme_path", str(demo_dir / "README.md"))
    return payload
