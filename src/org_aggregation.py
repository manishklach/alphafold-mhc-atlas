from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from .data_access import safe_read_csv
from .workspace import load_workspace_config, WorkspaceConfig


def aggregate_organization_data(workspace_root: Path) -> dict[str, pd.DataFrame]:
    """Aggregate portfolio and operational data across all workspaces in root."""
    all_portfolio_dfs = []
    all_projects_dfs = []
    all_health_dfs = []
    
    # 1. Discover workspaces
    # We look for .yaml files that look like workspace configs
    for ws_file in workspace_root.glob("*.yaml"):
        try:
            config = load_workspace_config(ws_file)
        except Exception:
            continue
            
        # 2. Aggregation Logic
        # Pull from Phase 19 portfolio outputs
        port_path = config.output_dir / "portfolio" / "portfolio_prioritization.csv"
        if port_path.exists():
            df = safe_read_csv(port_path)
            df["workspace_id"] = config.workspace_id
            all_portfolio_dfs.append(df)
            
        # Pull from Phase 15 workspace projects
        proj_path = config.output_dir / "workspace_projects.csv"
        if proj_path.exists():
            df = safe_read_csv(proj_path)
            df["workspace_id"] = config.workspace_id
            all_projects_dfs.append(df)

        # Pull from Program Memory (Decision Lineage etc)
        memory_dir = config.output_dir / "program_memory"
        if memory_dir.exists():
            # Basic health proxy: closure rates, unresolved carryforward
            metrics_path = memory_dir / "workflow_metrics.csv"
            if metrics_path.exists():
                df = safe_read_csv(metrics_path)
                df["workspace_id"] = config.workspace_id
                all_health_dfs.append(df)

    org_portfolio = pd.concat(all_portfolio_dfs, ignore_index=True) if all_portfolio_dfs else pd.DataFrame()
    org_projects = pd.concat(all_projects_dfs, ignore_index=True) if all_projects_dfs else pd.DataFrame()
    org_health = pd.concat(all_health_dfs, ignore_index=True) if all_health_dfs else pd.DataFrame()

    return {
        "org_portfolio_summary.csv": org_portfolio,
        "org_projects_summary.csv": org_projects,
        "org_health_baseline.csv": org_health
    }


def write_org_aggregation(workspace_root: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = aggregate_organization_data(workspace_root)
    
    paths = {}
    for filename, df in data.items():
        path = output_dir / filename
        df.to_csv(path, index=False)
        paths[filename] = path
        
    return paths
