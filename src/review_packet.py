from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pandas as pd

from .action_planning import build_action_plan
from .data_access import safe_read_text
from .next_actions import build_next_actions
from .open_questions import build_open_questions
from .project_history import build_project_history
from .role_views import export_role_views
from .scope_text import brief_scope_markdown, expanded_scope_markdown
from .workspace import WorkspaceConfig, load_workspace_config
from .workspace_index import build_workspace_inventory, write_workspace_inventory


def generate_project_review_packet(project_dir: Path, packet_id: str | None = None) -> Path:
    packet_id = packet_id or _default_packet_id("project")
    history_path = build_project_history(project_dir)
    next_actions_path = build_next_actions(project_dir)
    open_questions_path = build_open_questions(project_dir)
    action_plan_path = build_action_plan(project_dir)
    role_paths = export_role_views(project_dir)

    packet_dir = project_dir / "review_packets" / packet_id
    tables_dir = packet_dir / "review_packet_tables"
    figures_dir = packet_dir / "review_packet_figures"
    packet_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    table_paths = []
    for relative in [
        "analysis/summary.csv",
        "analysis/variant_priority_table.csv",
        "analysis/optimized_mutation_panel.csv",
        "review/shortlist.csv",
        "analysis/next_action_table.csv",
        "analysis/open_questions.csv",
    ]:
        source = project_dir / relative
        if source.exists():
            target = tables_dir / source.name
            shutil.copy2(source, target)
            table_paths.append({"source_path": str(source), "bundled_path": str(target)})

    summary = {
        "packet_id": packet_id,
        "project_name": project_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "change_summary_path": str(history_path.parent / "change_summary.md"),
        "next_actions_path": str(next_actions_path),
        "open_questions_path": str(open_questions_path),
        "role_views": {name: str(path) for name, path in role_paths.items()},
    }
    lines = [
        f"# Weekly Review Packet: {project_dir.name}",
        "",
        "## Overview",
        "",
        f"- Packet id: {packet_id}",
        f"- Generated at: {summary['generated_at']}",
        "",
        "## What changed since last review",
        "",
        safe_read_text(history_path.parent / "change_summary.md") or "No change summary available.",
        "",
        "## Open questions",
        "",
        safe_read_text(project_dir / "analysis" / "open_questions.md") or "No open questions available.",
        "",
        "## Next actions",
        "",
        safe_read_text(action_plan_path) or "No action plan available.",
        "",
        brief_scope_markdown(),
        "",
        expanded_scope_markdown(),
    ]
    (packet_dir / "review_packet.md").write_text("\n".join(lines), encoding="utf-8")
    (packet_dir / "change_summary.md").write_text(safe_read_text(history_path.parent / "change_summary.md"), encoding="utf-8")
    (packet_dir / "open_questions.md").write_text(safe_read_text(project_dir / "analysis" / "open_questions.md"), encoding="utf-8")
    (packet_dir / "next_actions.md").write_text(safe_read_text(action_plan_path), encoding="utf-8")
    (packet_dir / "review_packet_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(table_paths).to_csv(packet_dir / "packet_manifest.csv", index=False)
    return packet_dir


def generate_workspace_review_packet(workspace: WorkspaceConfig | str | Path, packet_id: str | None = None) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    packet_id = packet_id or _default_packet_id("workspace")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_workspace_inventory(config)
    inventory = build_workspace_inventory(config)
    packet_dir = config.output_dir / "review_packets" / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = packet_dir / "review_packet_tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(inventory["projects"]).to_csv(tables_dir / "workspace_projects.csv", index=False)
    pd.DataFrame(inventory["summary"]).to_csv(tables_dir / "workspace_summary.csv", index=False)
    (packet_dir / "change_summary.md").write_text(_workspace_change_summary(config), encoding="utf-8")
    (packet_dir / "open_questions.md").write_text(_workspace_open_questions(config), encoding="utf-8")
    (packet_dir / "next_actions.md").write_text(_workspace_next_actions(config), encoding="utf-8")
    (packet_dir / "review_packet.md").write_text(
        "\n".join(
            [
                f"# Weekly Review Packet: {config.name}",
                "",
                f"- Workspace id: {config.workspace_id}",
                f"- Projects included: {len(config.projects)}",
                "",
                "## Workspace summary",
                "",
                safe_read_text(packet_dir / "change_summary.md"),
                "",
                "## Open questions",
                "",
                safe_read_text(packet_dir / "open_questions.md"),
                "",
                "## Next actions",
                "",
                safe_read_text(packet_dir / "next_actions.md"),
                "",
                brief_scope_markdown(),
            ]
        ),
        encoding="utf-8",
    )
    (packet_dir / "review_packet_summary.json").write_text(json.dumps(inventory["summary"], indent=2), encoding="utf-8")
    pd.DataFrame(
        [
            {"bundled_path": str(tables_dir / "workspace_projects.csv"), "description": "Workspace project inventory"},
            {"bundled_path": str(tables_dir / "workspace_summary.csv"), "description": "Workspace summary table"},
        ]
    ).to_csv(packet_dir / "packet_manifest.csv", index=False)
    return packet_dir


def _default_packet_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def _workspace_change_summary(config: WorkspaceConfig) -> str:
    lines = ["# Workspace Change Summary", ""]
    for project in config.projects:
        history_path = build_project_history(project.path) if project.path.exists() else None
        summary = safe_read_text(history_path.parent / "change_summary.md") if history_path else "Project path missing."
        lines.extend([f"## {project.project_id}", "", summary, ""])
    return "\n".join(lines)


def _workspace_open_questions(config: WorkspaceConfig) -> str:
    lines = ["# Workspace Open Questions", ""]
    for project in config.projects:
        if not project.path.exists():
            lines.append(f"- {project.project_id}: project path missing.")
            continue
        build_open_questions(project.path)
        lines.extend([f"## {project.project_id}", "", safe_read_text(project.path / "analysis" / "open_questions.md") or "No open questions.", ""])
    return "\n".join(lines)


def _workspace_next_actions(config: WorkspaceConfig) -> str:
    lines = ["# Workspace Next Actions", ""]
    for project in config.projects:
        if not project.path.exists():
            lines.append(f"- {project.project_id}: project path missing.")
            continue
        build_action_plan(project.path)
        lines.extend([f"## {project.project_id}", "", safe_read_text(project.path / "analysis" / "action_plan.md"), ""])
    return "\n".join(lines)
