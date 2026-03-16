from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from .data_access import safe_read_csv, safe_read_text
from .workspace import WorkspaceConfig, load_workspace_config
from .retrospective_templates import get_retrospective_template, RetrospectiveTemplate
from .pattern_synthesis import synthesize_patterns
from .retrospective_selection import select_retrospective_artifacts
from .retrospective_views import build_role_retrospectives
from .meeting_outline import build_meeting_outlines
from .scope_text import expanded_scope_markdown


def build_retrospective_report(
    workspace: WorkspaceConfig | str | Path,
    template_id: str,
    report_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    template = get_retrospective_template(template_id)
    report_id = report_id or f"retro_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"

    output_dir = config.output_dir / "retrospectives" / report_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ensure memory is up to date (this might be too slow if called too often)
    # For Phase 14, we assume user might have run memory-summaries recently,
    # but we'll re-run pattern synthesis.
    synthesize_patterns(config.output_dir)
    selection = select_retrospective_artifacts(config.output_dir)

    # 2. Build the main report
    report_path = output_dir / "retrospective_report.md"
    lines = [
        f"# Retrospective Report: {template.label}",
        f"**Report ID**: {report_id}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        template.description,
        ""
    ]

    memory_dir = config.output_dir / "program_memory"

    if "executive_summary" in template.sections:
        lines.append("## Executive Summary")
        m_df = safe_read_csv(memory_dir / "multicycle_decision_summary.csv")
        lines.append(f"- Total unique entities tracked across cycles: {len(m_df) if not m_df.empty else 0}")
        o_df = safe_read_csv(memory_dir / "outcomes_summary.csv")
        lines.append(f"- Total follow-up outcomes captured: {o_df['count'].sum() if not o_df.empty else 0}")
        lines.append("")

    if "pattern_synthesis" in template.sections:
        lines.append("## Pattern Synthesis")
        patterns_df = safe_read_csv(memory_dir / "pattern_synthesis.csv")
        if not patterns_df.empty:
            for idx, row in patterns_df.iterrows():
                lines.append(f"### {row['category'].replace('_', ' ').title()}")
                lines.append(f"- {row['description']}")
                lines.append(f"- **Evidence Strength**: {row['evidence_strength']}")
        else:
            lines.append("- No recurring patterns were identified.")
        lines.append("")

    if "execution_flow" in template.sections:
        lines.append("## Execution Flow")
        metrics_df = safe_read_csv(memory_dir / "execution_metrics.csv")
        if not metrics_df.empty:
            for _, row in metrics_df.iterrows():
                lines.append(f"- **{row['metric'].replace('_', ' ').title()}**: {row['value']}")
        else:
            lines.append("- No execution metrics found.")
        lines.append("")

    lines.append("## Caveats and Scientific Guardrails")
    lines.append(expanded_scope_markdown())

    report_path.write_text("\n".join(lines), encoding="utf-8")

    # 3. Create role views and outlines
    role_paths = build_role_retrospectives(output_dir, template, memory_dir)
    outline_paths = build_meeting_outlines(output_dir, template, report_id)

    # 4. Create manifest files
    pd.DataFrame([{"table_name": t, "path": str(memory_dir / t)} for t in selection["selected_tables"]]).to_csv(output_dir / "retrospective_tables_manifest.csv", index=False)
    
    summary = {
        "report_id": report_id,
        "template_id": template_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": template.sections,
        "selected_tables": selection["selected_tables"],
        "role_views": {k: str(v) for k, v in role_paths.items()},
        "outlines": {k: str(v) for k, v in outline_paths.items()}
    }
    (output_dir / "retrospective_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    result = {
        "retrospective_report.md": report_path,
        "retrospective_summary.json": output_dir / "retrospective_summary.json",
        "retrospective_tables_manifest.csv": output_dir / "retrospective_tables_manifest.csv"
    }
    result.update(role_paths)
    result.update(outline_paths)
    return result
