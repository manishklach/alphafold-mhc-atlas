from __future__ import annotations

from typing import Any


def pre_execution_policy(context: Any, task_input: dict[str, Any]) -> dict[str, Any]:
    required_keys = ("candidate_id", "wt_file", "mutant_file")
    if any(not task_input.get(key) for key in required_keys):
        return {"allowed": False, "reason": "missing required input"}
    return {"allowed": True, "reason": ""}


def post_execution_policy(context: Any, output: dict[str, Any]) -> dict[str, Any]:
    modified_output = dict(output)
    warnings: list[str] = []

    final_output = dict(modified_output.get("final_output", {}))
    ranking = dict(final_output.get("ranking", {}))
    confidence_summary = dict(final_output.get("confidence_summary", {}))

    mutant_confidence = confidence_summary.get("mutant_avg_confidence")
    confidence_delta = confidence_summary.get("confidence_delta")

    if ranking.get("priority_label") == "HIGH" and mutant_confidence is not None and float(mutant_confidence) < 50:
        ranking["priority_label"] = "MEDIUM"
        ranking["flags"] = sorted(set([*ranking.get("flags", []), "runtime_low_confidence_warning"]))
        warnings.append("High-priority result was downgraded because mutant confidence is low.")

    if confidence_delta is not None and float(confidence_delta) < 0:
        ranking["flags"] = sorted(set([*ranking.get("flags", []), "runtime_confidence_warning"]))
        warnings.append("Confidence decreased relative to the WT structure.")

    final_output["ranking"] = ranking
    confidence_summary["flags"] = ranking.get("flags", [])
    final_output["confidence_summary"] = confidence_summary
    modified_output["final_output"] = final_output
    return {
        "allowed": True,
        "modified_output": modified_output,
        "warnings": warnings,
    }
