from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pandas as pd

from .data_access import safe_read_csv, safe_read_text
from .packet_templates import resolve_packet_template
from .review_packet import generate_project_review_packet, generate_workspace_review_packet
from .scope_text import brief_scope_markdown
from .workflow_templates import get_workflow_template
from .workspace import WorkspaceConfig, load_workspace_config


def generate_project_decision_packet(project_dir: Path, packet_id: str | None = None, workflow_template_name: str | None = None) -> Path:
    packet_id = packet_id or f"decision_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    workflow_template = get_workflow_template(workflow_template_name) if workflow_template_name else None
    packet_template = resolve_packet_template("decision", workflow_template)
    review_packet_dir = generate_project_review_packet(project_dir, workflow_template_name=workflow_template_name)
    packet_dir = project_dir / "decision_packets" / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    tables_manifest_rows = []
    for source in [
        project_dir / "review" / "shortlist.csv",
        project_dir / "analysis" / "optimized_mutation_panel.csv",
        project_dir / "analysis" / "open_questions.csv",
        project_dir / "analysis" / "next_action_table.csv",
    ]:
        if source.exists():
            target = packet_dir / source.name
            shutil.copy2(source, target)
            tables_manifest_rows.append({"table_id": source.stem, "source_path": str(source), "bundled_path": str(target)})
    (packet_dir / "meeting_brief.md").write_text(
        "\n".join(
            [
                f"# Decision Packet: {project_dir.name}",
                "",
                "Meeting-ready summary for internal decision review.",
                "",
                f"## Executive Meeting Focus ({packet_template.name})",
                "",
                safe_read_text(review_packet_dir / "change_summary.md") or "No change summary available.",
                "",
                "## Questions That Need Explicit Review",
                "",
                safe_read_text(project_dir / "analysis" / "open_questions.md") or "No open questions available.",
                "",
                "## Proposed Next Actions",
                "",
                safe_read_text(project_dir / "analysis" / "action_plan.md") or "No action plan available.",
                "",
                "## Caveats",
                "",
                brief_scope_markdown(),
            ]
        ),
        encoding="utf-8",
    )
    (packet_dir / "executive_summary.md").write_text(
        "\n".join(
            [
                "# Executive Summary",
                "",
                f"- Shortlist rows: {len(safe_read_csv(project_dir / 'review' / 'shortlist.csv'))}",
                f"- Panel rows: {len(safe_read_csv(project_dir / 'analysis' / 'optimized_mutation_panel.csv'))}",
                f"- Open questions: {len(safe_read_csv(project_dir / 'analysis' / 'open_questions.csv'))}",
                "- Best used for weekly team review, not as a scientific conclusion document.",
                "",
                "Manager-facing summaries remain exploratory and evidence-linked.",
            ]
        ),
        encoding="utf-8",
    )
    (packet_dir / "open_questions.md").write_text(safe_read_text(project_dir / "analysis" / "open_questions.md"), encoding="utf-8")
    (packet_dir / "next_actions.md").write_text(safe_read_text(project_dir / "analysis" / "action_plan.md"), encoding="utf-8")
    (packet_dir / "caveats.md").write_text(brief_scope_markdown(), encoding="utf-8")
    pd.DataFrame(columns=["figure_id", "source_path", "bundled_path"]).to_csv(packet_dir / "figures_manifest.csv", index=False)
    pd.DataFrame(tables_manifest_rows).to_csv(packet_dir / "tables_manifest.csv", index=False)
    return packet_dir


def generate_workspace_decision_packet(
    workspace: WorkspaceConfig | str | Path,
    packet_id: str | None = None,
    workflow_template_name: str | None = None,
) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    packet_id = packet_id or f"decision_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    workflow_template = get_workflow_template(workflow_template_name) if workflow_template_name else None
    packet_template = resolve_packet_template("decision", workflow_template)
    review_packet_dir = generate_workspace_review_packet(config, workflow_template_name=workflow_template_name)
    packet_dir = config.output_dir / "decision_packets" / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "meeting_brief.md").write_text(
        "\n".join(
            [
                f"# Workspace Decision Packet: {config.name}",
                "",
                "Meeting-ready summary for recurring cross-project review.",
                "",
                f"## Executive Meeting Focus ({packet_template.name})",
                "",
                safe_read_text(review_packet_dir / "review_packet.md"),
                "",
                "## Caveats",
                "",
                brief_scope_markdown(),
            ]
        ),
        encoding="utf-8",
    )
    (packet_dir / "executive_summary.md").write_text(
        "\n".join(
            [
                "# Executive Summary",
                "",
                f"- Projects in workspace: {len(config.projects)}",
                "- This packet is intended for recurring review meetings, not as scientific validation.",
            ]
        ),
        encoding="utf-8",
    )
    shutil.copy2(review_packet_dir / "review_packet_tables" / "workspace_summary.csv", packet_dir / "workspace_summary.csv")
    pd.DataFrame(
        [{"table_id": "workspace_summary", "source_path": str(review_packet_dir / "review_packet_tables" / "workspace_summary.csv"), "bundled_path": str(packet_dir / "workspace_summary.csv")}]
    ).to_csv(packet_dir / "tables_manifest.csv", index=False)
    pd.DataFrame(columns=["figure_id", "source_path", "bundled_path"]).to_csv(packet_dir / "figures_manifest.csv", index=False)
    (packet_dir / "open_questions.md").write_text(safe_read_text(review_packet_dir / "open_questions.md"), encoding="utf-8")
    (packet_dir / "next_actions.md").write_text(safe_read_text(review_packet_dir / "next_actions.md"), encoding="utf-8")
    (packet_dir / "caveats.md").write_text(brief_scope_markdown(), encoding="utf-8")
    return packet_dir
