from __future__ import annotations

from typing import Any

from core.scoring.prioritization import rank_candidates


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    comparison_results = input_data["comparison_results"]
    ranked = rank_candidates(comparison_results)
    return {
        "agent": "prioritization_agent",
        "input": {"num_candidates": len(comparison_results)},
        "output": ranked,
    }


def run_prioritization_agent(comparison_results: list[dict[str, Any]]) -> dict[str, Any]:
    return run({"comparison_results": comparison_results})
