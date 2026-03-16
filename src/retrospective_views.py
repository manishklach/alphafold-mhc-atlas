from __future__ import annotations

from pathlib import Path
from .data_access import safe_read_csv, safe_read_text
from .retrospective_templates import RetrospectiveTemplate


def build_role_retrospectives(
    output_dir: Path,
    template: RetrospectiveTemplate,
    memory_dir: Path
) -> dict[str, Path]:
    paths = {}
    
    if "scientist" in template.role_views:
        path = output_dir / "retrospective_scientist.md"
        lines = ["# Scientist Retrospective", "", "Focus: Evidence, rationale evolution, and structural caveats.", ""]
        rationale_df = safe_read_csv(memory_dir / "rationale_lineage.csv")
        if not rationale_df.empty:
            lines.append("## Rationale Evolution Patterns")
            lines.append(f"- Items with rationale recorded: {len(rationale_df)}")
        lines.append("\n## Caveats\nRetrospective summaries are descriptive context, not biological ground truth.")
        path.write_text("\n".join(lines), encoding="utf-8")
        paths["scientist"] = path

    if "manager" in template.role_views:
        path = output_dir / "retrospective_manager.md"
        lines = ["# Manager Retrospective", "", "Focus: Program velocity, follow-through, and attention items.", ""]
        m_df = safe_read_csv(memory_dir / "multicycle_decision_summary.csv")
        if not m_df.empty:
            lines.append("## Program Overview")
            lines.append(f"- Items tracked: {len(m_df)}")
        lines.append("\n## Caveats\nManager views should not be interpreted as validated scientific claims.")
        path.write_text("\n".join(lines), encoding="utf-8")
        paths["manager"] = path

    if "comp_lead" in template.role_views:
        path = output_dir / "retrospective_comp_lead.md"
        lines = ["# Comp Lead Retrospective", "", "Focus: Workflow effectiveness and execution bottlenecks.", ""]
        eff_df = safe_read_csv(memory_dir / "template_effectiveness_summary.csv")
        if not eff_df.empty:
            lines.append("## Workflow Effectiveness")
            for _, row in eff_df.iterrows():
                lines.append(f"- **{row['template_name']}**: Average unresolved: {row['avg_unresolved_carryforward']}")
        path.write_text("\n".join(lines), encoding="utf-8")
        paths["comp_lead"] = path

    return paths
