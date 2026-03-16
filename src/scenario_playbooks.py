from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from .scenario_state import ScenarioState
from .playbook_schema import Playbook, get_playbook
from .scenario_analysis import run_scenario_analysis


def playbook_to_scenario(playbook: Playbook, scenario_id: str | None = None) -> ScenarioState:
    return ScenarioState(
        scenario_id=scenario_id or f"pb_{playbook.playbook_id}",
        label=playbook.display_name,
        ranking_mode=playbook.ranking_mode,
        alleles=playbook.filters.get("alleles", []),
        peptides=playbook.filters.get("peptides", []),
        mutation_positions=playbook.filters.get("mutation_positions", []),
        substitutions=playbook.filters.get("substitutions", []),
        evidence_coverage_threshold=playbook.evidence_coverage_threshold,
        allowed_uncertainty=playbook.allowed_uncertainty,
        require_structural_support=playbook.require_structural_support,
        anchor_only=playbook.filters.get("anchor_only", False),
        case_study_id=playbook.filters.get("case_study_id"),
        panel_size=playbook.filters.get("panel_size"),
        notes=f"Generated from playbook: {playbook.playbook_id}. {playbook.description}",
    )


def run_playbook(
    workspace_dir: Path,
    playbook_id: str,
    tables: dict[str, pd.DataFrame],
    output_dir: Path | None = None
) -> dict[str, object]:
    playbook = get_playbook(playbook_id)
    scenario = playbook_to_scenario(playbook)
    
    result = run_scenario_analysis(scenario, tables, output_dir)
    
    # Add playbook specific metadata
    result["playbook"] = playbook.to_dict()
    
    if output_dir:
        (output_dir / "playbook_metadata.json").write_text(json.dumps(playbook.to_dict(), indent=2), encoding="utf-8")
        
    return result
