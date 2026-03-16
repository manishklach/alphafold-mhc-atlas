from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv


def synthesize_patterns(workspace_dir: Path) -> dict[str, pd.DataFrame]:
    memory_dir = workspace_dir / "program_memory"
    
    rationale_df = safe_read_csv(memory_dir / "rationale_lineage.csv")
    outcomes_df = safe_read_csv(memory_dir / "outcomes_log.csv")
    execution_df = safe_read_csv(memory_dir / "action_outcome_trace.csv")
    unresolved_df = safe_read_csv(memory_dir / "unresolved_questions.csv")

    patterns: list[dict[str, object]] = []

    # 1. Rationale-Outcome Pathways
    if not rationale_df.empty and not outcomes_df.empty:
        # Merge to find patterns of rationale leading to specific outcome classes
        # This is already partially in src/outcomes.py as rationale_to_outcome_patterns.csv
        # We'll pull from there if it exists or re-derive
        pathway_df = safe_read_csv(memory_dir / "rationale_to_outcome_patterns.csv")
        if not pathway_df.empty:
            for idx, row in pathway_df.head(5).iterrows():
                patterns.append({
                    "pattern_id": f"p_rat_out_{idx}",
                    "category": "rationale_outcome_link",
                    "description": f"Rationale category '{row.get('rationale_category')}' associated with outcome '{row.get('outcome_class')}' ({row.get('count')} times).",
                    "supporting_entities_count": row.get("count", 0),
                    "evidence_strength": "moderate" if row.get("count", 0) > 2 else "thin",
                    "caution_notes": "Associational only. Rationale categories are subjective tags."
                })

    # 2. Unresolved Question Patterns
    if not unresolved_df.empty:
        # Group unresolved questions by category
        q_patterns = unresolved_df.groupby("category").size().reset_index(name="count").sort_values("count", ascending=False)
        for idx, row in q_patterns.iterrows():
            patterns.append({
                "pattern_id": f"p_unres_q_{idx}",
                "category": "unresolved_bottleneck",
                "description": f"Repeated unresolved questions in category '{row.get('category')}' ({row.get('count')} times).",
                "supporting_entities_count": row.get("count", 0),
                "evidence_strength": "moderate" if row.get("count", 0) > 3 else "thin",
                "caution_notes": "Indicates persistent information gaps or review bottlenecks."
            })

    # 3. Execution Blockages
    blocked_df = safe_read_csv(memory_dir / "blocked_reasons_summary.csv")
    if not blocked_df.empty:
        b_patterns = blocked_df.groupby("owner_role").size().reset_index(name="count").sort_values("count", ascending=False)
        for idx, row in b_patterns.iterrows():
            patterns.append({
                "pattern_id": f"p_blocked_{idx}",
                "category": "execution_bottleneck",
                "description": f"Tasks assigned to role '{row.get('owner_role')}' are frequently blocked ({row.get('count')} items).",
                "supporting_entities_count": row.get("count", 0),
                "evidence_strength": "moderate" if row.get("count", 0) > 2 else "thin",
                "caution_notes": "Operational bottleneck, possibly indicating resource or role-clarity issues."
            })

    patterns_df = pd.DataFrame(patterns)
    if patterns_df.empty:
        patterns_df = pd.DataFrame(columns=["pattern_id", "category", "description", "supporting_entities_count", "evidence_strength", "caution_notes"])
    
    # Save patterns to disk
    patterns_df.to_csv(memory_dir / "pattern_synthesis.csv", index=False)
    
    # Generate a digest
    digest_path = memory_dir / "pattern_digest.md"
    lines = ["# Pattern Synthesis Digest", "", "Conservative identification of recurring review and execution patterns.", ""]
    if patterns_df.empty:
        lines.append("- No recurring patterns were identified from the current artifacts.")
    else:
        for _, row in patterns_df.iterrows():
            lines.append(f"## {row['category'].replace('_', ' ').title()}")
            lines.append(f"- **Description**: {row['description']}")
            lines.append(f"- **Evidence Strength**: {row['evidence_strength']}")
            lines.append(f"- **Caution**: {row['caution_notes']}")
            lines.append("")
    
    digest_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "pattern_synthesis.csv": patterns_df,
        "pattern_digest.md": digest_path
    }
