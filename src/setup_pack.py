from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import shutil
import yaml

import pandas as pd

from .workspace import WorkspaceConfig, load_workspace_config
from .resource_paths import repo_or_resource_path


def create_setup_pack(
    workspace: WorkspaceConfig | str | Path,
    pack_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    pack_id = pack_id or f"setup_pack_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"

    output_dir = config.output_dir / "setup_packs" / pack_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy Workspace Config
    shutil.copy(config.source_path, output_dir / "workspace_config_copy.yaml")

    # 2. Setup Template Manifest
    template_path = repo_or_resource_path("data", "setup_pack_template.yaml")
    if template_path.exists():
        payload = yaml.safe_load(template_path.read_text(encoding="utf-8")).get("setup_pack", {})
    else:
        payload = {"required_templates": [], "required_commands": [], "expected_structure": [], "caveats": []}

    pd.DataFrame([{"template_path": t} for t in payload.get("required_templates", [])]).to_csv(output_dir / "required_templates_manifest.csv", index=False)
    
    # 3. Artifact Manifest
    pd.DataFrame([{"artifact_path": p} for p in payload.get("expected_structure", [])]).to_csv(output_dir / "required_artifacts_manifest.csv", index=False)

    # 4. Commands MD
    cmd_lines = ["# Setup Commands", ""]
    for cmd in payload.get("required_commands", []):
        cmd_lines.append(f"```bash\n{cmd.replace('<workspace_file>', str(config.source_path))}\n```\n")
    (output_dir / "setup_commands.md").write_text("\n".join(cmd_lines), encoding="utf-8")

    # 5. Readme and Caveats
    readme_lines = [
        f"# Workspace Setup Pack: {config.name}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This pack contains the necessary files and instructions to deploy this workspace locally.",
        "See `setup_commands.md` for initialization commands."
    ]
    (output_dir / "setup_pack_readme.md").write_text("\n".join(readme_lines), encoding="utf-8")

    caveat_lines = ["# Scope and Caveats", ""] + [f"- {c}" for c in payload.get("caveats", [])]
    (output_dir / "scope_and_caveats.md").write_text("\n".join(caveat_lines), encoding="utf-8")

    return {
        "setup_pack_readme.md": output_dir / "setup_pack_readme.md",
        "workspace_config_copy.yaml": output_dir / "workspace_config_copy.yaml",
        "required_templates_manifest.csv": output_dir / "required_templates_manifest.csv",
        "required_artifacts_manifest.csv": output_dir / "required_artifacts_manifest.csv",
        "setup_commands.md": output_dir / "setup_commands.md",
        "scope_and_caveats.md": output_dir / "scope_and_caveats.md",
        "pack_dir": output_dir
    }
