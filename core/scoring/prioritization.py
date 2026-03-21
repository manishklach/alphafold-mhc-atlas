from __future__ import annotations

from typing import Any


def rank_candidates(comparison_results_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for index, item in enumerate(comparison_results_list):
        candidate_id = str(item.get("candidate_id") or item.get("entity_id") or f"candidate_{index + 1}")
        comparison = item.get("comparison") if isinstance(item.get("comparison"), dict) else item

        avg_shift = float(comparison.get("avg_shift", comparison.get("structure_shift_score") or 0.0))
        max_shift = float(comparison.get("max_shift") or 0.0)
        large_shift_count = int(comparison.get("large_shift_count") or 0)
        confidence_delta = float(comparison.get("confidence_delta") or 0.0)
        flags = [str(flag) for flag in comparison.get("flags", [])]
        legacy_mean_confidence = (comparison.get("confidence_summary") or {}).get("mean_confidence")
        confidence_penalty = 0.5 if avg_shift < 1.0 else 1.0

        raw_score = 0.0
        reasons: list[str] = []

        if avg_shift > 2.0:
            raw_score += 3
            reasons.append(f"avg shift {avg_shift:.2f} > 2.0 (+3)")
        elif avg_shift > 1.0:
            raw_score += 2
            reasons.append(f"avg shift {avg_shift:.2f} > 1.0 (+2)")
        else:
            reasons.append(f"avg shift {avg_shift:.2f} (+0)")

        large_shift_bonus = min(large_shift_count, 3)
        if large_shift_bonus:
            raw_score += large_shift_bonus
            reasons.append(f"{large_shift_count} large shift(s) (+{large_shift_bonus})")

        if confidence_delta < -5:
            raw_score -= confidence_penalty
            reasons.append(f"confidence delta {confidence_delta:.2f} < -5 (-{confidence_penalty:g})")
        else:
            reasons.append(f"confidence delta {confidence_delta:.2f} (no penalty)")

        if "high_structural_change" in flags:
            raw_score += 3
            reasons.append("flag high_structural_change (+3)")
        if "confidence_drop" in flags:
            raw_score -= confidence_penalty
            reasons.append(f"flag confidence_drop (-{confidence_penalty:g})")
        if legacy_mean_confidence is not None and float(legacy_mean_confidence) < 70:
            flags.append("low_confidence")
            reasons.append(f"legacy mean confidence {float(legacy_mean_confidence):.1f} < 70 (flag only)")

        priority_score = _normalize_score(raw_score)
        priority_label = _priority_label(priority_score)
        explanation = _build_explanation(
            avg_shift=avg_shift,
            max_shift=max_shift,
            large_shift_count=large_shift_count,
            confidence_delta=confidence_delta,
            reasons=reasons,
        )
        ranked.append(
            {
                "candidate_id": candidate_id,
                "priority_score": priority_score,
                "priority_label": priority_label,
                "explanation": explanation,
                "flags": sorted(set(flags)),
            }
        )

    return sorted(ranked, key=lambda item: (-float(item["priority_score"]), str(item["candidate_id"])))


def _normalize_score(raw_score: float) -> float:
    clamped = max(0.0, min(raw_score, 10.0))
    return round(clamped, 2)


def _priority_label(priority_score: float) -> str:
    if priority_score >= 7:
        return "HIGH"
    if priority_score >= 4:
        return "MEDIUM"
    return "LOW"


def _build_explanation(
    avg_shift: float,
    max_shift: float,
    large_shift_count: int,
    confidence_delta: float,
    reasons: list[str],
) -> str:
    structural_change = _structural_change_label(avg_shift)
    impact_label = _impact_label(avg_shift, large_shift_count)

    first_sentence = f"{structural_change} structural change observed (avg shift {avg_shift:.1f} Å, max {max_shift:.1f} Å)."
    if large_shift_count > 1:
        first_sentence = (
            f"{structural_change} structural change observed (avg shift {avg_shift:.1f} Å, "
            f"max {max_shift:.1f} Å) with multiple large deviations."
        )
    elif large_shift_count == 1:
        first_sentence = (
            f"{structural_change} structural change observed (avg shift {avg_shift:.1f} Å, "
            f"max {max_shift:.1f} Å) with one large deviation."
        )

    second_parts = [f"Mutation impact appears {impact_label}."]
    if confidence_delta < -5:
        second_parts.append("Confidence decreased, indicating potential instability.")
    elif any("legacy mean confidence" in reason for reason in reasons):
        second_parts.append("Confidence is low, so this result should be interpreted cautiously.")
    elif confidence_delta > 0:
        second_parts.append("Confidence improved relative to the reference structure.")

    return " ".join([first_sentence, " ".join(second_parts)])


def _structural_change_label(avg_shift: float) -> str:
    if avg_shift > 2.0:
        return "Significant"
    if avg_shift > 1.0:
        return "Moderate"
    return "Low"


def _impact_label(avg_shift: float, large_shift_count: int) -> str:
    if avg_shift > 2.0 or large_shift_count > 1:
        return "significant"
    if avg_shift > 1.0 or large_shift_count == 1:
        return "moderate"
    return "limited"
