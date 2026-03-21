from __future__ import annotations

from typing import Any

from biology.comparisons.comparison_engine import compare_structures


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    wt_structure = input_data["wt_structure"]
    mutant_structure = input_data["mutant_structure"]
    comparison = compare_structures(wt_structure, mutant_structure)
    return {
        "agent": "comparison_agent",
        "input": {
            "wt_residue_count": len(wt_structure.get("residues", [])),
            "mutant_residue_count": len(mutant_structure.get("residues", [])),
        },
        "output": comparison,
    }


def run_comparison_agent(wt_structure: dict[str, Any], mutant_structure: dict[str, Any]) -> dict[str, Any]:
    return run({"wt_structure": wt_structure, "mutant_structure": mutant_structure})
