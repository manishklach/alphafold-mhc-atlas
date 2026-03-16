from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class Playbook:
    playbook_id: str
    display_name: str
    description: str
    intended_use: str
    ranking_mode: str
    evidence_coverage_threshold: float
    allowed_uncertainty: list[str]
    require_structural_support: bool
    benchmark_mode: str
    outcome_mode: str
    role_emphasis: str
    caution_notes: str
    filters: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "playbook_id": self.playbook_id,
            "display_name": self.display_name,
            "description": self.description,
            "intended_use": self.intended_use,
            "ranking_mode": self.ranking_mode,
            "evidence_coverage_threshold": self.evidence_coverage_threshold,
            "allowed_uncertainty": self.allowed_uncertainty,
            "require_structural_support": self.require_structural_support,
            "benchmark_mode": self.benchmark_mode,
            "outcome_mode": self.outcome_mode,
            "role_emphasis": self.role_emphasis,
            "caution_notes": self.caution_notes,
            "filters": self.filters,
        }


def load_playbooks(path: Path | None = None) -> list[Playbook]:
    if path is None:
        path = repo_or_resource_path("data", "playbook_templates.yaml")
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("playbooks", []) if isinstance(payload, dict) else []
    return [Playbook(**t) for t in templates if isinstance(t, dict)]


def get_playbook(playbook_id: str) -> Playbook:
    playbooks = load_playbooks()
    for p in playbooks:
        if p.playbook_id == playbook_id:
            return p
    raise ValueError(f"Playbook '{playbook_id}' not found.")
