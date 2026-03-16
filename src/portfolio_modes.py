from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class CapacityTemplate:
    capacity_id: str
    max_do_now: int
    max_discuss_soon: int
    max_escalate: int


@dataclass(frozen=True)
class PortfolioMode:
    mode_id: str
    label: str
    description: str
    capacity_id: str
    primary_sort: str


def load_capacity_templates(path: Path | None = None) -> list[CapacityTemplate]:
    path = path or repo_or_resource_path("data", "capacity_templates.yaml")
    if not path.exists():
        return [CapacityTemplate("default", 10, 10, 5)]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [CapacityTemplate(**c) for c in data.get("capacity_templates", [])]


def load_portfolio_modes(path: Path | None = None) -> list[PortfolioMode]:
    path = path or repo_or_resource_path("data", "portfolio_modes.yaml")
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [PortfolioMode(**m) for m in data.get("modes", [])]


def get_portfolio_mode(mode_id: str) -> PortfolioMode:
    for m in load_portfolio_modes():
        if m.mode_id == mode_id:
            return m
    raise ValueError(f"Portfolio mode '{mode_id}' not found.")

def get_capacity_template(capacity_id: str) -> CapacityTemplate:
    for c in load_capacity_templates():
        if c.capacity_id == capacity_id:
            return c
    return CapacityTemplate("default", 10, 10, 5)
