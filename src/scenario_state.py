from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ScenarioState:
    scenario_id: str
    label: str
    ranking_mode: str
    alleles: list[str]
    peptides: list[str]
    mutation_positions: list[int]
    substitutions: list[str]
    evidence_coverage_threshold: float
    allowed_uncertainty: list[str]
    require_structural_support: bool
    anchor_only: bool
    case_study_id: str | None
    panel_size: int | None
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def save_scenario_state(scenario: ScenarioState, path: Path) -> Path:
    path.write_text(scenario.to_json(), encoding="utf-8")
    return path


def load_scenario_state(path: Path) -> ScenarioState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ScenarioState(**payload)
