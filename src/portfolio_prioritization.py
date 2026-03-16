from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .portfolio_modes import get_portfolio_mode, get_capacity_template


def build_portfolio_prioritization(
    workspace: WorkspaceConfig | str | Path,
    mode_id: str = "evidence_first_capacity_mode"
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    out_dir = config.output_dir / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = get_portfolio_mode(mode_id)
    capacity = get_capacity_template(mode.capacity_id)

    candidates_path = out_dir / "portfolio_candidates.csv"
    if not candidates_path.exists():
        return {}
        
    df = safe_read_csv(candidates_path)
    if df.empty:
        df["priority_bucket"] = []
        df.to_csv(out_dir / "portfolio_prioritization.csv", index=False)
        return {"portfolio_prioritization.csv": out_dir / "portfolio_prioritization.csv"}

    # Scoring heuristic based on mode
    def _score(row: pd.Series) -> float:
        score = 0.0
        ar = str(row.get("analytical_robustness_label", ""))
        hr = str(row.get("human_robustness_label", ""))
        
        if mode.primary_sort == "analytical_robustness":
            if ar == "robust_across_playbooks": score += 10
            elif ar == "moderately_stable": score += 5
            if hr == "consensus_robust": score += 2 # Tie breaker
        elif mode.primary_sort == "human_consensus":
            if hr == "consensus_robust": score += 10
            elif hr == "consensus_fragile": score += 5
            if ar == "robust_across_playbooks": score += 2 # Tie breaker
            
        return score

    df["attention_score"] = df.apply(_score, axis=1)
    df = df.sort_values("attention_score", ascending=False).reset_index(drop=True)

    # Assign buckets using capacity limits
    buckets = []
    do_now_count = 0
    discuss_count = 0
    
    for _, row in df.iterrows():
        hr = str(row.get("human_robustness_label", ""))
        
        if hr == "disputed_judgment":
            buckets.append("escalate")
            continue
            
        if do_now_count < capacity.max_do_now:
            buckets.append("do_now")
            do_now_count += 1
        elif discuss_count < capacity.max_discuss_soon:
            buckets.append("discuss_soon")
            discuss_count += 1
        else:
            buckets.append("monitor")
            
    df["priority_bucket"] = buckets
    df["prioritization_mode"] = mode_id
    
    out_path = out_dir / "portfolio_prioritization.csv"
    df.to_csv(out_path, index=False)
    
    # Capacity summary
    summary_path = out_dir / "capacity_planning_summary.md"
    lines = [
        f"# Capacity Planning Summary",
        f"- **Mode**: {mode.label}",
        f"- **Capacity Template**: {capacity.capacity_id}",
        "",
        "## Allocations",
        f"- **do_now**: {do_now_count} / {capacity.max_do_now}",
        f"- **discuss_soon**: {discuss_count} / {capacity.max_discuss_soon}",
        f"- **escalate**: {df['priority_bucket'].value_counts().get('escalate', 0)} / {capacity.max_escalate}",
        f"- **monitor**: {df['priority_bucket'].value_counts().get('monitor', 0)}",
        "",
        "## Caveats",
        "Buckets represent operational focus under bandwidth constraints, not validation of scientific truth."
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "portfolio_prioritization.csv": out_path,
        "capacity_planning_summary.md": summary_path
    }
