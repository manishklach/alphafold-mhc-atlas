from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import yaml
import pandas as pd

from .workspace import WorkspaceConfig, load_workspace_config
from .resource_paths import repo_or_resource_path

def create_evaluation_pack(
    workspace: WorkspaceConfig | str | Path
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    output_dir = config.output_dir / "evaluation_pack"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = repo_or_resource_path("data", "pilot_evaluation_template.yaml")
    if not template_path.exists():
        raise FileNotFoundError("pilot_evaluation_template.yaml not found.")
        
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    
    # 1. Guide
    guide_path = output_dir / "PILOT_EVALUATION_GUIDE.md"
    guide_lines = [
        "# Pilot Evaluation Guide",
        f"**Workspace**: {config.name}",
        "",
        "This guide helps teams evaluate the structural decision platform in a 1-2 week pilot.",
        "",
        "## What is in scope",
        "- Structure-guided mutation review",
        "- Role-based operational tracking",
        "- Retrospective synthesis of review patterns",
        "",
        "## What is out of scope",
        "- Direct binding affinity prediction",
        "- Replacement of wet-lab validation",
        "- Automated adjustments of structural rankings based on outcomes",
    ]
    guide_path.write_text("\n".join(guide_lines), encoding="utf-8")
    
    # 2. Questions
    q_path = output_dir / "evaluation_questions.md"
    q_lines = ["# Evaluation Questions", ""]
    for q in payload.get("evaluation_questions", []):
        q_lines.append(f"- **{q['id']}**: {q['question']}")
    q_path.write_text("\n".join(q_lines), encoding="utf-8")
    
    # 3. Success Criteria
    sc_path = output_dir / "evaluation_success_criteria.md"
    sc_lines = ["# Success Criteria", ""]
    for s in payload.get("success_criteria", []):
        sc_lines.append(f"- [ ] {s}")
    sc_path.write_text("\n".join(sc_lines), encoding="utf-8")
    
    # 4. Checklist CSV
    cl_path = output_dir / "evaluation_checklist.csv"
    pd.DataFrame([{"step": c, "status": "pending"} for c in payload.get("checklists", [])]).to_csv(cl_path, index=False)
    
    # 5. Manifest
    manifest_path = output_dir / "evaluation_artifact_manifest.csv"
    manifest_rows = [
        {"artifact": "PILOT_EVALUATION_GUIDE.md", "description": "Main guide"},
        {"artifact": "evaluation_questions.md", "description": "Core questions to answer"},
        {"artifact": "evaluation_success_criteria.md", "description": "Definition of pilot success"},
        {"artifact": "evaluation_checklist.csv", "description": "Trackable checklist"}
    ]
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    
    return {
        "PILOT_EVALUATION_GUIDE.md": guide_path,
        "evaluation_questions.md": q_path,
        "evaluation_success_criteria.md": sc_path,
        "evaluation_checklist.csv": cl_path,
        "evaluation_artifact_manifest.csv": manifest_path
    }
