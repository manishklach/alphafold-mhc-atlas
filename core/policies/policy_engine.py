from __future__ import annotations

from typing import Any


def apply_policies(ranking_output: dict[str, Any]) -> dict[str, Any]:
    result = dict(ranking_output)
    flags = list(result.get("flags", []))
    explanation = str(result.get("explanation") or "")
    priority_score = float(result.get("priority_score", 0.0))
    priority_label = str(result.get("priority_label") or "LOW")

    comparison = result.get("comparison", {}) if isinstance(result.get("comparison"), dict) else {}
    avg_shift = float(comparison.get("avg_shift", 0.0))
    confidence_delta = float(comparison.get("confidence_delta", 0.0))
    mutant_confidence = result.get("mutant_confidence")

    if mutant_confidence is not None and float(mutant_confidence) < 50 and priority_label == "HIGH":
        priority_label = "MEDIUM"
        priority_score = min(priority_score, 6.99)
        flags.append("policy_block_high_low_confidence")

    if avg_shift <= 0 and priority_label == "HIGH":
        priority_label = "MEDIUM"
        priority_score = min(priority_score, 6.99)
        flags.append("policy_block_high_no_structural_change")

    if confidence_delta < -5:
        flags.append("uncertainty")
        if explanation and "uncertainty" not in explanation.lower():
            explanation = f"{explanation} Uncertainty remains elevated because confidence decreased."

    result["priority_score"] = round(priority_score, 2)
    result["priority_label"] = priority_label
    result["flags"] = sorted(set(flags))
    result["explanation"] = explanation.strip()
    return result
