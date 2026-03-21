from __future__ import annotations

from typing import Any

RESIDUE_CATEGORIES = {
    "A": "hydrophobic",
    "V": "hydrophobic",
    "I": "hydrophobic",
    "L": "hydrophobic",
    "M": "hydrophobic",
    "F": "hydrophobic",
    "W": "hydrophobic",
    "Y": "hydrophobic",
    "S": "polar",
    "T": "polar",
    "N": "polar",
    "Q": "polar",
    "K": "charged",
    "R": "charged",
    "H": "charged",
    "D": "charged",
    "E": "charged",
    "C": "special",
    "G": "special",
    "P": "special",
}
THREE_TO_ONE = {
    "ALA": "A",
    "VAL": "V",
    "ILE": "I",
    "LEU": "L",
    "MET": "M",
    "PHE": "F",
    "TRP": "W",
    "TYR": "Y",
    "SER": "S",
    "THR": "T",
    "ASN": "N",
    "GLN": "Q",
    "LYS": "K",
    "ARG": "R",
    "HIS": "H",
    "ASP": "D",
    "GLU": "E",
    "CYS": "C",
    "GLY": "G",
    "PRO": "P",
}


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
        mutant_confidence = _extract_mutant_confidence(comparison)
        if mutant_confidence is not None and float(mutant_confidence) < 70:
            flags.append("low_confidence")

        score_breakdown = {
            "structural": _structural_impact_score(avg_shift, max_shift, large_shift_count, flags),
            "confidence": _confidence_impact_score(confidence_delta, mutant_confidence),
            "mutation": _mutation_severity_score(comparison.get("residue_changes", [])),
            "consistency": _consistency_score(
                avg_shift,
                large_shift_count,
                flags,
                comparison.get("residue_changes", []),
                confidence_delta,
            ),
        }
        priority_score = _priority_score(score_breakdown)
        priority_label = _priority_label(priority_score)
        explanation = _build_explanation(
            avg_shift=avg_shift,
            max_shift=max_shift,
            large_shift_count=large_shift_count,
            confidence_delta=confidence_delta,
            mutant_confidence=mutant_confidence,
            score_breakdown=score_breakdown,
            residue_changes=comparison.get("residue_changes", []),
            priority_label=priority_label,
        )
        ranked.append(
            {
                "candidate_id": candidate_id,
                "priority_score": priority_score,
                "priority_label": priority_label,
                "explanation": explanation,
                "flags": sorted(set(flags)),
                "score_breakdown": score_breakdown,
            }
        )

    return sorted(ranked, key=lambda item: (-float(item["priority_score"]), str(item["candidate_id"])))


def _weighted_priority_score(score_breakdown: dict[str, float]) -> float:
    weighted = sum(score_breakdown.values())
    return round(max(0.0, min(weighted, 10.0)), 2)


def _priority_score(score_breakdown: dict[str, float]) -> float:
    return _weighted_priority_score(score_breakdown)


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
    mutant_confidence: float | None,
    score_breakdown: dict[str, float],
    residue_changes: list[dict[str, Any]],
    priority_label: str,
) -> str:
    sentences = [
        _structural_sentence(avg_shift, max_shift, large_shift_count),
        _mutation_sentence(residue_changes, score_breakdown["mutation"]),
    ]

    confidence_sentence = _confidence_sentence(confidence_delta, mutant_confidence, score_breakdown["confidence"])
    if confidence_sentence:
        sentences.append(confidence_sentence)

    sentences.append(
        _final_interpretation_sentence(
            score_breakdown=score_breakdown,
            priority_label=priority_label,
        )
    )
    return " ".join(sentence for sentence in sentences if sentence)


def _structural_change_label(avg_shift: float) -> str:
    if avg_shift > 2.0:
        return "Significant"
    if avg_shift > 1.0:
        return "Moderate"
    return "Low"


def _impact_label(structural_score: float, mutation_score: float) -> str:
    if structural_score >= 4.0 or mutation_score >= 1.5:
        return "significant"
    if structural_score >= 2.0 or mutation_score >= 1.0:
        return "moderate"
    return "limited"


def _moderate_impact_sentence(avg_shift: float, large_shift_count: int) -> str:
    if avg_shift > 1.0 or large_shift_count == 1:
        if large_shift_count >= 1:
            return "The shift pattern suggests a localized conformational change that may affect residue presentation or local packing."
        return "The observed displacement suggests a localized conformational perturbation rather than a global rearrangement."
    return ""


def _confidence_sentence(confidence_delta: float, mutant_confidence: float | None, confidence_score: float) -> str:
    if confidence_delta < -5:
        if mutant_confidence is not None and mutant_confidence < 70:
            return "Confidence decreased and remains relatively low, indicating meaningful uncertainty but not enough to erase the observed structural signal."
        return "Confidence decreased moderately, indicating some uncertainty in the structural interpretation."
    if mutant_confidence is not None and mutant_confidence < 70:
        return "Absolute confidence is relatively low, so the result should be interpreted cautiously."
    if confidence_score <= -1.0:
        return "Confidence is limited, so this result should be interpreted cautiously."
    return ""


def _structural_impact_score(
    avg_shift: float,
    max_shift: float,
    large_shift_count: int,
    flags: list[str],
) -> float:
    score = 0.0
    if avg_shift >= 2.5:
        score += 3.0
    elif avg_shift >= 1.5:
        score += 2.0
    elif avg_shift >= 1.0:
        score += 1.5
    elif avg_shift >= 0.5:
        score += 0.5

    if max_shift >= 3.0:
        score += 1.0
    elif max_shift >= 2.0:
        score += 0.75
    elif max_shift >= 1.0:
        score += 0.25

    score += min(large_shift_count, 2) * 0.5
    if "high_structural_change" in flags:
        score += 0.5
    return round(min(score, 5.0), 2)


def _confidence_impact_score(
    confidence_delta: float,
    mutant_confidence: float | None,
) -> float:
    score = 0.0
    if confidence_delta <= -15:
        score -= 1.0
    elif confidence_delta <= -8:
        score -= 0.75
    elif confidence_delta <= -5:
        score -= 0.5
    elif confidence_delta < 0:
        score -= 0.25

    if mutant_confidence is not None:
        if mutant_confidence < 50:
            score -= 0.75
        elif mutant_confidence < 70:
            score -= 0.5
    return round(max(-1.5, min(score, 0.0)), 2)


def _mutation_severity_score(residue_changes: list[dict[str, Any]]) -> float:
    severity = 0.0
    for change in residue_changes:
        if change.get("change_type") != "mutated":
            continue
        wt_category = _residue_category(change.get("wt_residue_name"))
        mutant_category = _residue_category(change.get("mutant_residue_name"))
        if wt_category and mutant_category and wt_category != mutant_category:
            if {"hydrophobic", "polar"} == {wt_category, mutant_category} or (
                "charged" in {wt_category, mutant_category} and wt_category != mutant_category
            ):
                severity = max(severity, 2.0)
            else:
                severity = max(severity, 1.0)
        elif change.get("wt_residue_name") != change.get("mutant_residue_name"):
            severity = max(severity, 0.5)
    return round(min(severity, 2.0), 2)


def _consistency_score(
    avg_shift: float,
    large_shift_count: int,
    flags: list[str],
    residue_changes: list[dict[str, Any]],
    confidence_delta: float,
) -> float:
    mutation_score = _mutation_severity_score(residue_changes)
    if avg_shift >= 2.0 and ("high_structural_change" in flags or mutation_score >= 1.0) and confidence_delta > -10:
        return 1.0
    if avg_shift >= 1.0 and (large_shift_count > 0 or mutation_score > 0 or bool(flags)):
        return 0.5
    return 0.0


def _extract_mutant_confidence(comparison: dict[str, Any]) -> float | None:
    for value in (
        comparison.get("mutant_confidence"),
        (comparison.get("confidence_summary") or {}).get("avg"),
        (comparison.get("confidence_summary") or {}).get("mean_confidence"),
    ):
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _residue_category(residue_name: Any) -> str | None:
    if residue_name is None:
        return None
    residue = str(residue_name).upper()
    if len(residue) == 3:
        residue = THREE_TO_ONE.get(residue, residue)
    return RESIDUE_CATEGORIES.get(residue)


def _structural_sentence(avg_shift: float, max_shift: float, large_shift_count: int) -> str:
    deviation = _structural_change_label(avg_shift).lower()
    if large_shift_count > 1:
        return (
            f"{deviation.capitalize()} structural deviation observed (avg shift {avg_shift:.1f} Å, "
            f"max {max_shift:.1f} Å) with multiple large residue shifts."
        )
    if large_shift_count == 1:
        return (
            f"{deviation.capitalize()} structural deviation observed (avg shift {avg_shift:.1f} Å, "
            f"max {max_shift:.1f} Å) with one large residue shift."
        )
    return f"{deviation.capitalize()} structural deviation observed (avg shift {avg_shift:.1f} Å, max {max_shift:.1f} Å)."


def _mutation_sentence(residue_changes: list[dict[str, Any]], mutation_score: float) -> str:
    transition = _dominant_mutation_transition(residue_changes)
    if transition is None:
        if mutation_score >= 1.5:
            return "The residue substitution introduces a strong biochemical change that could disrupt local interactions."
        if mutation_score >= 1.0:
            return "The residue substitution introduces a moderate biochemical change that may alter local contacts."
        return "The residue substitution is biochemically mild, suggesting limited direct chemical disruption."

    wt_group, mutant_group = transition
    severity = "substantial" if mutation_score >= 1.5 else "moderate" if mutation_score >= 1.0 else "mild"
    if mutation_score >= 1.5:
        return (
            f"The mutation introduces a {severity} biochemical change from {wt_group} to {mutant_group} residue, "
            "suggesting potential disruption of local interactions."
        )
    if mutation_score >= 1.0:
        return (
            f"The mutation shifts residue chemistry from {wt_group} to {mutant_group}, "
            "which may alter local packing or interaction preferences."
        )
    return (
        f"The mutation changes residue chemistry from {wt_group} to {mutant_group}, "
        "but the biochemical shift appears mild."
    )


def _dominant_mutation_transition(residue_changes: list[dict[str, Any]]) -> tuple[str, str] | None:
    best_transition: tuple[str, str] | None = None
    best_score = -1.0
    for change in residue_changes:
        if change.get("change_type") != "mutated":
            continue
        wt_category = _residue_category(change.get("wt_residue_name"))
        mutant_category = _residue_category(change.get("mutant_residue_name"))
        if wt_category is None or mutant_category is None:
            continue
        transition_score = _transition_severity(wt_category, mutant_category)
        if transition_score > best_score:
            best_score = transition_score
            best_transition = (wt_category, mutant_category)
    return best_transition


def _transition_severity(wt_category: str, mutant_category: str) -> float:
    if wt_category == mutant_category:
        return 0.0
    if {"hydrophobic", "polar"} == {wt_category, mutant_category}:
        return 2.0
    if "charged" in {wt_category, mutant_category}:
        return 2.0
    if "special" in {wt_category, mutant_category}:
        return 1.0
    return 1.0


def _final_interpretation_sentence(score_breakdown: dict[str, float], priority_label: str) -> str:
    if priority_label == "HIGH":
        return "Overall, this mutation is prioritized due to strong structural and biochemical impact."
    if priority_label == "MEDIUM":
        return "Overall, this mutation is prioritized as a plausible follow-up because the structural and biochemical signals are directionally aligned."
    if score_breakdown["structural"] >= 2.0:
        return "Overall, the mutation shows some structural signal, but the combined evidence is not strong enough for high-priority follow-up."
    return "Overall, the combined signals suggest limited evidence for a high-priority structural effect."
