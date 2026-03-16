from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_attention_queues(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    out_dir = config.output_dir / "portfolio"
    
    prioritization_path = out_dir / "portfolio_prioritization.csv"
    if not prioritization_path.exists():
        return {}
        
    df = safe_read_csv(prioritization_path)
    if df.empty:
        return {}

    # Scientist Queue: do_now
    sci_q = df[df["priority_bucket"] == "do_now"].copy()
    sci_q["target_role"] = "scientist"
    sci_q["queue_reason"] = "Allocated to do_now bucket based on capacity and robustness."
    sci_path = out_dir / "scientist_attention_queue.csv"
    sci_q.to_csv(sci_path, index=False)

    # Manager Queue: discuss_soon + escalate
    mgr_q = df[df["priority_bucket"].isin(["discuss_soon", "escalate"])].copy()
    mgr_q["target_role"] = "manager"
    mgr_q["queue_reason"] = "Requires management discussion or dispute resolution."
    mgr_path = out_dir / "manager_attention_queue.csv"
    mgr_q.to_csv(mgr_path, index=False)
    
    # Escalation Queue: specifically disputed items
    esc_q = df[df["priority_bucket"] == "escalate"].copy()
    esc_q["queue_reason"] = "Disputed judgment requiring team meeting alignment."
    esc_path = out_dir / "escalation_queue.csv"
    esc_q.to_csv(esc_path, index=False)

    return {
        "scientist_attention_queue.csv": sci_path,
        "manager_attention_queue.csv": mgr_path,
        "escalation_queue.csv": esc_path
    }
