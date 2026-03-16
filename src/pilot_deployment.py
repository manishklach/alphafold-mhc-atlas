from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import json

from .workspace import WorkspaceConfig, load_workspace_config
from .deployment_checks import run_deployment_checks

def check_pilot_readiness(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    results = run_deployment_checks(config)
    
    output_dir = config.output_dir / "pilot_readiness"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "pilot_readiness_report.md"
    summary_path = output_dir / "pilot_readiness_summary.json"
    checklist_path = output_dir / "deployment_checklist.csv"
    missing_path = output_dir / "missing_setup_items.csv"
    
    # Write Report
    lines = [
        f"# Pilot Readiness Report: {config.name}",
        f"**Workspace ID**: {config.workspace_id}",
        "",
        "## Overall Status",
        f"Ready for Pilot Evaluation: {'Yes' if results['is_ready'] else 'No'}",
        "",
        "## Checks",
    ]
    for check in results["checks"]:
        status = "Pass" if check["passed"] else "Fail"
        lines.append(f"- **{check['name']}**: {status}")
        if not check["passed"]:
            lines.append(f"  - *Reason*: {check['reason']}")
            
    lines.extend([
        "",
        "## Scope and Caveats",
        "This checks structural readiness for a pilot. It does not validate scientific predictions. The framework remains an exploratory tool."
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    
    # Write JSON
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    
    # Write CSVs
    import pandas as pd
    pd.DataFrame(results["checks"]).to_csv(checklist_path, index=False)
    
    missing_items = [c for c in results["checks"] if not c["passed"]]
    if missing_items:
        pd.DataFrame(missing_items).to_csv(missing_path, index=False)
    else:
        pd.DataFrame(columns=["name", "passed", "reason"]).to_csv(missing_path, index=False)

    return {
        "pilot_readiness_report.md": report_path,
        "pilot_readiness_summary.json": summary_path,
        "deployment_checklist.csv": checklist_path,
        "missing_setup_items.csv": missing_path
    }
