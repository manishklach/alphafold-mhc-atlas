from __future__ import annotations

from pathlib import Path
from .retrospective_templates import RetrospectiveTemplate


def build_meeting_outlines(
    output_dir: Path,
    template: RetrospectiveTemplate,
    report_id: str
) -> dict[str, Path]:
    meeting_path = output_dir / "meeting_outline.md"
    slide_path = output_dir / "slide_outline.md"

    m_lines = [
        f"# Meeting Outline: {template.label}",
        f"**Report ID**: {report_id}",
        "",
        "## Suggested Agenda",
        "1. Executive Summary & Program Velocity",
        "2. Key Recurring Patterns (Review & Execution)",
        "3. Workflow Effectiveness & Bottlenecks",
        "4. Critical Caveats & Next Planning Window",
        "",
        "## Discussion Points",
        "- Which unresolved questions are most frequently carried forward?",
        "- Are specific roles consistently blocked in execution?",
    ]
    meeting_path.write_text("\n".join(m_lines), encoding="utf-8")

    s_lines = [
        f"# Slide Outline: {template.label}",
        "",
        "## Slide 1: Retrospective Overview",
        f"- {template.label}",
        f"- Generated: {report_id}",
        "",
        "## Slide 2: Program Activity",
        "- Items reviewed vs. advanced",
        "- Outcomes captured",
        "",
        "## Slide 3: Recurring Patterns",
        "- Rationale-to-outcome co-occurrence",
        "- Bottleneck categories",
        "",
        "## Slide 4: Scientific Caveats",
        "- Exploratory structural analysis only",
        "- Not biological ground truth",
    ]
    slide_path.write_text("\n".join(s_lines), encoding="utf-8")

    return {
        "meeting_outline.md": meeting_path,
        "slide_outline.md": slide_path
    }
