from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .workspace import WorkspaceConfig, load_workspace_config
from .workspace_index import build_workspace_inventory


def build_program_memory(workspace: WorkspaceConfig | str | Path) -> Path:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    config.output_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_workspace_inventory(config)
    output_path = config.output_dir / "program_memory.json"
    output_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    pd.DataFrame(inventory["projects"]).to_csv(config.output_dir / "program_memory_projects.csv", index=False)
    return output_path
