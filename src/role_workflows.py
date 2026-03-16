from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import yaml
import pandas as pd

from .workspace import WorkspaceConfig, load_workspace_config
from .resource_paths import repo_or_resource_path

def export_role_workflows(
    workspace: WorkspaceConfig | str | Path,
    role_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    
    output_dir = config.output_dir / "role_workflows"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = repo_or_resource_path("data", "role_workflow_templates.yaml")
    if not template_path.exists():
        raise FileNotFoundError("role_workflow_templates.yaml not found.")
        
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    roles = payload.get("roles", [])
    
    if role_id:
        roles = [r for r in roles if r.get("role_id") == role_id]
        if not roles:
            raise ValueError(f"Role '{role_id}' not found in templates.")

    paths = {}
    manifest_rows = []
    
    for role in roles:
        rid = role.get("role_id")
        rname = role.get("name")
        file_name = f"role_workflow_{rid}.md"
        out_path = output_dir / file_name
        
        lines = [
            f"# Operating Workflow: {rname}",
            f"**Workspace**: {config.name}",
            "",
            "## Entrypoint",
            f"Start your review at: **{role.get('entrypoint')}**",
            "",
            "## Recommended Packets",
            "\n".join([f"- {p}" for p in role.get("recommended_packets", [])]),
            "",
            "## Key Questions to Ask",
            "\n".join([f"- {q}" for q in role.get("questions_to_ask", [])]),
            "",
            "## Outputs to Inspect",
            "\n".join([f"- {o}" for o in role.get("outputs_to_inspect", [])]),
            "",
            "## Common Pitfalls & Caveats",
            "\n".join([f"- **Caution**: {p}" for p in role.get("common_pitfalls", [])])
        ]
        
        out_path.write_text("\n".join(lines), encoding="utf-8")
        paths[file_name] = out_path
        
        manifest_rows.append({
            "role_id": rid,
            "role_name": rname,
            "file_name": file_name
        })
        
    manifest_path = output_dir / "role_workflow_manifest.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    paths["role_workflow_manifest.csv"] = manifest_path

    return paths
