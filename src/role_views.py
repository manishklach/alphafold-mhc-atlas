from __future__ import annotations

from pathlib import Path

from .data_access import safe_read_csv, safe_read_text
from .scope_text import brief_scope_markdown, expanded_scope_markdown


def export_role_views(project_dir: Path, output_dir: Path | None = None) -> dict[str, Path]:
    root = output_dir or (project_dir / "analysis" / "role_views")
    root.mkdir(parents=True, exist_ok=True)
    summary_df = safe_read_csv(project_dir / "analysis" / "summary.csv")
    priority_df = safe_read_csv(project_dir / "analysis" / "variant_priority_table.csv")
    panel_df = safe_read_csv(project_dir / "analysis" / "optimized_mutation_panel.csv")
    change_summary = safe_read_text(project_dir / "history" / "change_summary.md")
    next_actions = safe_read_text(project_dir / "analysis" / "action_plan.md")
    open_questions = safe_read_text(project_dir / "analysis" / "open_questions.md")

    scientist = [
        f"# Scientist View: {project_dir.name}",
        "",
        "Detailed evidence-first view for analyst review.",
        "",
        "## What To Review First",
        "",
        "- Inspect top ranked variants and their evidence bundles.",
        "- Check uncertainty and open questions before expanding the shortlist.",
        "",
        "## Evidence Focus",
        "",
        f"- Summary rows: {len(summary_df)}",
        f"- Prioritization rows: {len(priority_df)}",
        f"- Panel rows: {len(panel_df)}",
        "",
        change_summary or "No change summary available.",
        "",
        open_questions or "No open questions available.",
        "",
        expanded_scope_markdown(),
    ]
    comp_lead = [
        f"# Computational Lead View: {project_dir.name}",
        "",
        "Prioritization and workflow view for scenario, change, and coverage review.",
        "",
        "## What To Review First",
        "",
        "- Confirm what changed since the last review cycle.",
        "- Check whether current next actions are driven by strong enough support.",
        "",
        "## Workflow Summary",
        "",
        f"- Prioritization rows: {len(priority_df)}",
        f"- Panel rows: {len(panel_df)}",
        "",
        change_summary or "No change summary available.",
        "",
        next_actions or "No action plan available.",
        "",
        expanded_scope_markdown(),
    ]
    manager = [
        f"# Manager View: {project_dir.name}",
        "",
        "Meeting-ready summary intended for review, not proof.",
        "",
        "## What Needs Discussion This Week",
        "",
        f"- Shortlist candidates available: {len(safe_read_csv(project_dir / 'review' / 'shortlist.csv'))}",
        f"- Feedback entries logged: {len(safe_read_csv(project_dir / 'review' / 'feedback_log.csv'))}",
        "",
        "## Open Questions",
        "",
        open_questions or "No open questions available.",
        "",
        "## Next Actions",
        "",
        next_actions or "No action plan available.",
        "",
        "## Caveats",
        "",
        brief_scope_markdown(),
    ]
    paths = {
        "scientist": root / "role_view_scientist.md",
        "comp_lead": root / "role_view_comp_lead.md",
        "manager": root / "role_view_manager.md",
    }
    paths["scientist"].write_text("\n".join(scientist), encoding="utf-8")
    paths["comp_lead"].write_text("\n".join(comp_lead), encoding="utf-8")
    paths["manager"].write_text("\n".join(manager), encoding="utf-8")
    return paths
