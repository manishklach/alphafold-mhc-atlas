from __future__ import annotations

from typing import Any

from core.reporting.report_generator import generate_decision_report


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    ranked_candidates = input_data.get("ranked_candidates", [])
    pipeline_output = input_data.get("pipeline_output")
    top_candidates = ranked_candidates[:5]
    flagged_candidates = [
        {
            "candidate_id": candidate.get("candidate_id"),
            "flags": candidate.get("flags", []),
        }
        for candidate in ranked_candidates
        if candidate.get("flags")
    ]
    report_markdown = generate_decision_report(pipeline_output) if pipeline_output else None
    return {
        "agent": "review_agent",
        "input": {"num_ranked_candidates": len(ranked_candidates)},
        "output": {
            "top_candidates": top_candidates,
            "flagged_candidates": flagged_candidates,
            "report_generated": report_markdown is not None,
            "summary": {
                "num_candidates": len(ranked_candidates),
                "num_flagged": len(flagged_candidates),
            },
        },
    }


def run_review_agent(ranked_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return run({"ranked_candidates": ranked_candidates})
