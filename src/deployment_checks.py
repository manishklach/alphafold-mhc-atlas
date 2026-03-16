from __future__ import annotations

from pathlib import Path
from .workspace import WorkspaceConfig
from .resource_paths import repo_or_resource_path

def run_deployment_checks(config: WorkspaceConfig) -> dict[str, object]:
    checks = []
    
    # 1. Config Check
    checks.append({
        "name": "Workspace Configuration Valid",
        "passed": len(config.projects) > 0,
        "reason": "Workspace has no projects." if len(config.projects) == 0 else ""
    })
    
    # 2. Outputs Directory
    checks.append({
        "name": "Outputs Directory Exists",
        "passed": config.output_dir.exists(),
        "reason": f"Directory not found: {config.output_dir}" if not config.output_dir.exists() else ""
    })
    
    # 3. Core Templates
    templates = [
        "scenario_templates.yaml",
        "workflow_templates.yaml",
        "execution_templates.yaml",
        "retrospective_templates.yaml",
        "pilot_evaluation_template.yaml",
        "role_workflow_templates.yaml",
        "setup_pack_template.yaml"
    ]
    missing_templates = []
    for t in templates:
        if not repo_or_resource_path("data", t).exists():
            missing_templates.append(t)
            
    checks.append({
        "name": "Core Templates Present",
        "passed": len(missing_templates) == 0,
        "reason": f"Missing templates: {', '.join(missing_templates)}" if missing_templates else ""
    })

    # 4. Program Memory Baseline
    memory_dir = config.output_dir / "program_memory"
    has_memory = memory_dir.exists() and (memory_dir / "decision_lineage.csv").exists()
    checks.append({
        "name": "Program Memory Baseline Established",
        "passed": has_memory,
        "reason": "Missing program_memory/decision_lineage.csv. Run a review cycle first." if not has_memory else ""
    })

    is_ready = all(c["passed"] for c in checks)
    
    return {
        "is_ready": is_ready,
        "checks": checks
    }
