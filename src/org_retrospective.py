from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import yaml
import pandas as pd

from .data_access import safe_read_csv
from .resource_paths import repo_or_resource_path
from .scope_text import expanded_scope_markdown


def build_org_retrospective(
    workspace_root: Path,
    output_dir: Path,
    template_id: str = "quarterly_operating_review"
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Aggregate
    from .org_aggregation import aggregate_organization_data
    data = aggregate_organization_data(workspace_root)
    
    # 2. Load Template
    template_path = repo_or_resource_path("data", "org_review_templates.yaml")
    template = None
    if template_path.exists():
        payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        for t in payload.get("templates", []):
            if t.get("template_id") == template_id:
                template = t
                break
    
    if not template:
        template = {"label": "Org Retrospective", "sections": ["portfolio_overview", "caveats"]}

    # 3. Build Report
    report_path = output_dir / "org_retrospective_report.md"
    lines = [
        f"# Organization Retrospective: {template.get('label')}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"**Scope**: All workspaces in {workspace_root}",
        "",
    ]

    port_df = data["org_portfolio_summary.csv"]
    proj_df = data["org_projects_summary.csv"]
    health_df = data["org_health_baseline.csv"]

    if "portfolio_overview" in template.get("sections", []):
        lines.extend([
            "## Portfolio Overview",
            f"- Total candidates aggregated: {len(port_df)}",
            f"- Total active projects: {len(proj_df['project_id'].unique()) if not proj_df.empty else 0}",
            f"- Workspaces covered: {len(proj_df['workspace_id'].unique()) if not proj_df.empty else 0}",
            "",
        ])
        if not port_df.empty and "priority_bucket" in port_df.columns:
            lines.append("### Allocation by Priority Bucket")
            counts = port_df["priority_bucket"].value_counts().to_dict()
            for bucket, count in counts.items():
                lines.append(f"- **{bucket}**: {count}")
            lines.append("")

    if "workflow_health" in template.get("sections", []):
        lines.append("## Workflow Health")
        if not health_df.empty:
            avg_unres = health_df["avg_unresolved_carryforward"].mean() if "avg_unresolved_carryforward" in health_df.columns else 0
            lines.append(f"- **Average Unresolved Carry-forward**: {avg_unres:.2f}")
        else:
            lines.append("- No health data available.")
        lines.append("")

    lines.extend([
        "## Scientific Guardrails",
        expanded_scope_markdown()
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Save summary JSON
    summary = {
        "template_id": template_id,
        "total_items": len(port_df),
        "total_projects": len(proj_df["project_id"].unique()) if not proj_df.empty else 0,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    (output_dir / "org_retrospective_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "org_retrospective_report.md": report_path,
        "org_retrospective_summary.json": output_dir / "org_retrospective_summary.json"
    }
