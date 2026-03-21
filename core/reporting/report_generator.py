from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_report(
    ranked_candidates: list[dict[str, Any]],
    output_path: str | Path = "storage/reports/ranked_candidates_report.md",
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_build_report_markdown(ranked_candidates), encoding="utf-8")
    return target


def generate_decision_report(pipeline_output: dict[str, Any]) -> str:
    candidate_id = str(pipeline_output.get("candidate_id") or "unknown_candidate")
    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    comparison = pipeline_output.get("comparison", {})
    ranking = pipeline_output.get("ranking", {})
    wt_confidence = pipeline_output.get("wt_structure", {}).get("confidence_summary", {}).get("avg")
    mutant_confidence = pipeline_output.get("mutant_structure", {}).get("confidence_summary", {}).get("avg")
    confidence_delta = comparison.get("confidence_delta", 0.0)
    flags = [str(flag) for flag in ranking.get("flags", [])]

    markdown = "\n".join(
        [
            "# MHC Atlas Decision Report",
            "",
            "## Candidate",
            f"- ID: {candidate_id}",
            "",
            "## Structural Summary",
            f"- Avg Shift: {float(comparison.get('avg_shift', 0.0)):.3f} Å",
            f"- Max Shift: {float(comparison.get('max_shift', 0.0)):.3f} Å",
            f"- Large Shifts: {int(comparison.get('large_shift_count', 0))}",
            "",
            "## Confidence",
            f"- WT confidence: {_format_confidence(wt_confidence)}",
            f"- Mutant confidence: {_format_confidence(mutant_confidence)}",
            f"- Delta: {float(confidence_delta):.1f}",
            "",
            "## Decision",
            f"- Priority Score: {float(ranking.get('priority_score', 0.0)):.2f}",
            f"- Priority Label: {str(ranking.get('priority_label') or 'N/A')}",
            "",
            "## Interpretation",
            str(ranking.get("explanation") or "No interpretation available."),
            "",
            "## Flags",
            *(_human_readable_flags(flags) or ["- None"]),
            "",
            "## Why this matters",
            _why_this_matters(str(ranking.get("priority_label") or "")),
            "",
        ]
    )

    report_path = report_dir / f"{candidate_id}.md"
    report_path.write_text(markdown, encoding="utf-8")
    return markdown


def _build_report_markdown(ranked_candidates: list[dict[str, Any]]) -> str:
    lines = [
        "# Candidate Ranking Report",
        "",
        f"Total candidates: {len(ranked_candidates)}",
        "",
        "## Top Candidates",
        "",
    ]

    if not ranked_candidates:
        lines.extend(
            [
                "No ranked candidates were provided.",
                "",
            ]
        )
        return "\n".join(lines)

    for index, candidate in enumerate(ranked_candidates, start=1):
        candidate_id = str(candidate.get("candidate_id") or f"candidate_{index}")
        priority_score = float(candidate.get("priority_score") or 0.0)
        explanation = str(candidate.get("explanation") or "No explanation provided.")
        flags = [str(flag) for flag in candidate.get("flags", [])]

        lines.extend(
            [
                f"### {index}. {candidate_id}",
                "",
                f"- Priority score: {priority_score:.2f}",
                f"- Explanation: {explanation}",
                f"- Flags: {', '.join(flags) if flags else 'None'}",
                "",
            ]
        )

    return "\n".join(lines)


def _format_confidence(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}"


def _human_readable_flags(flags: list[str]) -> list[str]:
    if not flags:
        return []
    return [f"- {flag.replace('_', ' ').capitalize()}" for flag in flags]


def _why_this_matters(priority_label: str) -> str:
    if priority_label == "HIGH":
        return "Significant structural deviation suggests mutation could alter stability or binding."
    if priority_label == "MEDIUM":
        return "Moderate structural change suggests mutation may impact local behavior."
    return "Minimal structural deviation suggests mutation is unlikely to significantly alter function."
