from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def analyze_disagreement_drivers(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    memory_dir = config.output_dir / "program_memory"
    
    log_path = memory_dir / "reviewer_judgments.csv"
    df = safe_read_csv(log_path)
    if df.empty:
        return {}

    drivers = []
    
    for (etype, eid), group in df.groupby(["entity_type", "entity_id"]):
        if len(group) < 2:
            continue
            
        # Role-based divergence
        if group["reviewer_role"].nunique() > 1:
            role_judgments = group.groupby("reviewer_role")["judgment_label"].nunique()
            if role_judgments.max() > 1 or group["judgment_label"].nunique() > 1:
                drivers.append({
                    "driver_id": f"dr_{etype}_{eid}_role",
                    "entity_type": etype,
                    "entity_id": eid,
                    "driver_category": "role_divergence",
                    "description": f"Different roles ({group['reviewer_role'].unique().tolist()}) provided divergent judgments.",
                    "supporting_judgments_count": len(group)
                })
                
        # Playbook-based divergence
        if group["playbook_id"].nunique() > 1:
            drivers.append({
                "driver_id": f"dr_{etype}_{eid}_playbook",
                "entity_type": etype,
                "entity_id": eid,
                "driver_category": "playbook_divergence",
                "description": f"Judgments made under different playbooks ({group['playbook_id'].unique().tolist()}).",
                "supporting_judgments_count": len(group)
            })

        # Benchmark sensitivity
        if group["benchmark_mode"].nunique() > 1:
            drivers.append({
                "driver_id": f"dr_{etype}_{eid}_benchmark",
                "entity_type": etype,
                "entity_id": eid,
                "driver_category": "benchmark_sensitivity",
                "description": "Divergence between benchmark-aware and benchmark-blind review modes.",
                "supporting_judgments_count": len(group)
            })

    drivers_df = pd.DataFrame(drivers)
    drivers_path = memory_dir / "disagreement_drivers.csv"
    drivers_df.to_csv(drivers_path, index=False)
    
    return {"disagreement_drivers.csv": drivers_path}
