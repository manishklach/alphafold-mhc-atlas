from __future__ import annotations

from typing import Any

from .agent_runner import run_agent_pipeline


def route_task(task_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
    if task_type == "single_analysis":
        return run_agent_pipeline(
            candidate_id=str(input_data["candidate_id"]),
            wt_file=str(input_data["wt_file"]),
            mutant_file=str(input_data["mutant_file"]),
        )

    if task_type == "batch_analysis":
        candidates = input_data.get("candidates", [])
        results = [
            run_agent_pipeline(
                candidate_id=str(candidate["candidate_id"]),
                wt_file=str(candidate["wt_file"]),
                mutant_file=str(candidate["mutant_file"]),
            )
            for candidate in candidates
        ]
        successful_results = [result for result in results if result.get("status") == "success"]
        successful_results.sort(
            key=lambda item: float(item["final_output"]["ranking"]["priority_score"]),
            reverse=True,
        )
        error_results = [result for result in results if result.get("status") != "success"]
        return {
            "task_type": "batch_analysis",
            "status": "success",
            "results": successful_results + error_results,
            "top_candidates": successful_results[:3],
        }

    raise ValueError(f"Unsupported task_type: {task_type}")
