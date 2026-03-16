from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from .data_access import safe_read_csv


def compute_decision_robustness(
    sensitivity_results: list[dict],
    output_dir: Path
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Aggregate Variant Inclusion
    variant_counts = {}
    total_runs = len(sensitivity_results)
    
    for res in sensitivity_results:
        ranked = res["ranked_variants"]
        if ranked.empty:
            continue
        for vid in ranked["variant_id"].unique():
            variant_counts[vid] = variant_counts.get(vid, 0) + 1
            
    # 2. Build Robustness Table
    rows = []
    for vid, count in variant_counts.items():
        inclusion_rate = count / total_runs
        label = "robust_across_playbooks" if inclusion_rate >= 0.8 else \
                "moderately_stable" if inclusion_rate >= 0.5 else \
                "fragile_to_assumptions"
        
        rows.append({
            "entity_type": "variant",
            "entity_id": vid,
            "num_sensitivity_runs_seen": count,
            "total_runs": total_runs,
            "inclusion_rate": inclusion_rate,
            "robustness_label": label,
            "caution_notes": "Fragile items appear only under specific analytical assumptions." if label == "fragile_to_assumptions" else ""
        })
        
    robustness_df = pd.DataFrame(rows).sort_values("inclusion_rate", ascending=False).reset_index(drop=True)
    robustness_df.to_csv(output_dir / "robustness_summary.csv", index=False)
    
    robust_items = robustness_df[robustness_df["inclusion_rate"] >= 0.8]
    robust_items.to_csv(output_dir / "robust_items.csv", index=False)
    
    fragile_items = robustness_df[robustness_df["inclusion_rate"] < 0.5]
    fragile_items.to_csv(output_dir / "fragile_items.csv", index=False)

    # 3. Generate Digest
    digest = _build_robustness_digest(robustness_df, total_runs)
    (output_dir / "robustness_digest.md").write_text(digest, encoding="utf-8")

    return {
        "robustness_summary.csv": robustness_df,
        "robustness_digest.md": digest
    }


def _build_robustness_digest(df: pd.DataFrame, total_runs: int) -> str:
    if df.empty:
        return "# Decision Robustness Digest\n\nNo data available."
        
    robust_count = len(df[df["inclusion_rate"] >= 0.8])
    fragile_count = len(df[df["inclusion_rate"] < 0.5])
    
    lines = [
        "# Decision Robustness Digest",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Analyzed stability across **{total_runs}** sensitivity variations.",
        "",
        "## Summary",
        f"- **Robust Variants**: {robust_count} (seen in >= 80% of runs)",
        f"- **Fragile Variants**: {fragile_count} (seen in < 50% of runs)",
        "",
        "## Robust Selections",
        "These items consistently appear prioritized regardless of minor assumption changes.",
    ]
    for _, row in df[df["inclusion_rate"] >= 0.8].head(10).iterrows():
        lines.append(f"- **{row['entity_id']}**: {row['inclusion_rate']*100:.0f}% inclusion")
        
    lines.extend([
        "",
        "## Caveats",
        "Robustness indicates mathematical stability under different filters and weights. It does not validate biological truth. A robustly prioritized variant is a more stable hypothesis, not a proven binder."
    ])
    return "\n".join(lines)
