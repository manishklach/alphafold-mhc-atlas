from __future__ import annotations

from pathlib import Path

from .resource_paths import repo_or_resource_path

DEMO_ROOT = repo_or_resource_path("demo")


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
