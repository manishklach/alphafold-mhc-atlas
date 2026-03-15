from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
RESOURCE_ROOT = PACKAGE_ROOT / "resources"


def repo_or_resource_path(*parts: str) -> Path:
    repo_path = REPO_ROOT.joinpath(*parts)
    if repo_path.exists():
        return repo_path
    return RESOURCE_ROOT.joinpath(*parts)
