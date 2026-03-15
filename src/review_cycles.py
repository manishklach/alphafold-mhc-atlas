from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data_access import safe_read_json, safe_read_text
from .history_compare import build_history_diff_summary, compare_history_tables
from .workspace import WorkspaceConfig, load_workspace_config


def summarize_review_cycles(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "review_cycles"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    packet_root = config.output_dir / "review_packets"
    for packet_dir in sorted([path for path in packet_root.iterdir() if path.is_dir()], key=lambda item: item.name) if packet_root.exists() else []:
        summary = safe_read_json(packet_dir / "review_packet_summary.json")
        rows.append(
            {
                "cycle_id": packet_dir.name,
                "workspace_id": config.workspace_id,
                "generated_at": summary.get("generated_at"),
                "workflow_template": summary.get("workflow_template"),
                "packet_type": "review_packet",
                "num_projects": summary.get("num_projects", len(config.projects)),
                "notes": summary.get("change_summary_path") or "",
            }
        )
    summary_path = output_dir / "cycle_summary.csv"
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    change_log_path = output_dir / "cycle_change_log.md"
    if rows:
        lines = ["# Cycle Change Log", ""]
        for row in rows:
            lines.append(f"- `{row['cycle_id']}` generated at `{row.get('generated_at', 'unknown')}`.")
        change_log_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        change_log_path.write_text("# Cycle Change Log\n\n- No review cycles were found.\n", encoding="utf-8")
    comparison_path = output_dir / "cycle_to_cycle_comparison.csv"
    pd.DataFrame().to_csv(comparison_path, index=False)
    return {
        "cycle_summary.csv": summary_path,
        "cycle_change_log.md": change_log_path,
        "cycle_to_cycle_comparison.csv": comparison_path,
    }


def compare_review_cycles(workspace: WorkspaceConfig | str | Path, current_cycle: str, previous_cycle: str) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "review_cycles"
    output_dir.mkdir(parents=True, exist_ok=True)
    current_dir = config.output_dir / "review_packets" / current_cycle / "review_packet_tables" / "workspace_projects.csv"
    previous_dir = config.output_dir / "review_packets" / previous_cycle / "review_packet_tables" / "workspace_projects.csv"
    comparison_df = compare_history_tables(current_dir, previous_dir, ["project_id"])
    comparison_path = output_dir / "cycle_to_cycle_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)
    summary_path = output_dir / "cycle_change_log.md"
    summary_path.write_text(build_history_diff_summary(comparison_df, f"{previous_cycle} -> {current_cycle}"), encoding="utf-8")
    cycle_summary_path = output_dir / "cycle_summary.csv"
    if not cycle_summary_path.exists():
        summarize_review_cycles(config)
    return {
        "cycle_summary.csv": cycle_summary_path,
        "cycle_change_log.md": summary_path,
        "cycle_to_cycle_comparison.csv": comparison_path,
    }
