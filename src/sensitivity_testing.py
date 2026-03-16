from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

import pandas as pd

from .scenario_state import ScenarioState
from .scenario_playbooks import playbook_to_scenario, run_playbook
from .playbook_schema import Playbook, get_playbook
from .scenario_analysis import run_scenario_analysis


def run_sensitivity_suite(
    workspace_dir: Path,
    playbook_id: str,
    tables: dict[str, pd.DataFrame],
    output_dir: Path | None = None
) -> dict[str, object]:
    playbook = get_playbook(playbook_id)
    base_scenario = playbook_to_scenario(playbook)
    
    output_dir = output_dir or workspace_dir / "sensitivity" / f"{playbook_id}_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    results = []

    # 1. Baseline
    base_res = run_scenario_analysis(base_scenario, tables, output_dir / "baseline")
    runs.append({"run_id": "baseline", "type": "baseline", "params": base_scenario.to_dict()})
    results.append(base_res)

    # 2. Evidence Threshold Sensitivity
    for delta in [-0.1, 0.1]:
        new_thresh = max(0.0, min(1.0, base_scenario.evidence_coverage_threshold + delta))
        if new_thresh == base_scenario.evidence_coverage_threshold:
            continue
        run_id = f"evidence_threshold_{new_thresh:.1f}"
        s = _clone_scenario(base_scenario, run_id, evidence_coverage_threshold=new_thresh)
        res = run_scenario_analysis(s, tables, output_dir / run_id)
        runs.append({"run_id": run_id, "type": "threshold_perturbation", "params": s.to_dict()})
        results.append(res)

    # 3. Uncertainty Sensitivity
    all_uncertainty = ["low", "medium", "high", "insufficient_data"]
    # Tighter
    if len(base_scenario.allowed_uncertainty) > 1:
        run_id = "uncertainty_tighter"
        s = _clone_scenario(base_scenario, run_id, allowed_uncertainty=base_scenario.allowed_uncertainty[:1])
        res = run_scenario_analysis(s, tables, output_dir / run_id)
        runs.append({"run_id": run_id, "type": "uncertainty_perturbation", "params": s.to_dict()})
        results.append(res)
    # Looser
    if len(base_scenario.allowed_uncertainty) < len(all_uncertainty):
        run_id = "uncertainty_looser"
        s = _clone_scenario(base_scenario, run_id, allowed_uncertainty=all_uncertainty)
        res = run_scenario_analysis(s, tables, output_dir / run_id)
        runs.append({"run_id": run_id, "type": "uncertainty_perturbation", "params": s.to_dict()})
        results.append(res)

    # 4. Structural Support Sensitivity
    run_id = "toggle_structural_support"
    s = _clone_scenario(base_scenario, run_id, require_structural_support=not base_scenario.require_structural_support)
    res = run_scenario_analysis(s, tables, output_dir / run_id)
    runs.append({"run_id": run_id, "type": "structural_support_perturbation", "params": s.to_dict()})
    results.append(res)

    # Save Run Log
    runs_df = pd.DataFrame(runs)
    runs_df.to_csv(output_dir / "sensitivity_runs.csv", index=False)

    summary = _build_sensitivity_summary(playbook_id, runs, results)
    (output_dir / "sensitivity_summary.md").write_text(summary, encoding="utf-8")

    return {
        "runs": runs,
        "results": results,
        "output_dir": output_dir,
        "summary_markdown": summary
    }


def _clone_scenario(s: ScenarioState, new_id: str, **kwargs) -> ScenarioState:
    d = s.to_dict()
    d.update(kwargs)
    d["scenario_id"] = new_id
    return ScenarioState(**d)


def _build_sensitivity_summary(playbook_id: str, runs: list[dict], results: list[dict]) -> str:
    lines = [
        f"# Sensitivity Analysis: {playbook_id}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Run Overview",
    ]
    for run in runs:
        res = results[runs.index(run)]
        lines.append(f"- **{run['run_id']}** ({run['type']}): {len(res['ranked_variants'])} ranked, {len(res['panel'])} in panel.")
    
    lines.extend([
        "",
        "## Caveats",
        "Sensitivity analysis measures how much prioritization changes under different assumptions. It is a diagnostic tool for decision robustness, not biological verification."
    ])
    return "\n".join(lines)
