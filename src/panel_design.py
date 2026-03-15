from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PanelDesignConfig


@dataclass(frozen=True)
class PanelDesignResult:
    optimized_panel_df: pd.DataFrame
    panel_coverage_df: pd.DataFrame
    discriminatory_panel_df: pd.DataFrame
    balanced_panel_df: pd.DataFrame
    report_markdown: str


def run_panel_design(
    priority_df: pd.DataFrame,
    panel_config: PanelDesignConfig,
) -> PanelDesignResult:
    empty = PanelDesignResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "# Panel Design\n\nDisabled.\n")
    if not panel_config.enabled or priority_df.empty:
        return empty

    disruptive_panel = _select_panel(priority_df, "disruptive_mutations", "top_disruptive_panel", panel_config)
    tolerated_panel = _select_panel(priority_df, "tolerated_mutations", "top_tolerated_panel", panel_config)
    discriminatory_panel = _select_panel(
        priority_df, "allele_discriminating_mutations", "allele_discrimination_panel", panel_config
    )
    anchor_panel = _select_panel(priority_df, "anchor_sensitive_mutations", "anchor_behavior_panel", panel_config)
    balanced_mode_name = (
        panel_config.ranking_goal
        if panel_config.ranking_goal == "balanced_exploration_panel"
        else "exploratory_followup_candidates"
    )
    balanced_panel = _select_panel(priority_df, balanced_mode_name, "balanced_exploration_panel", panel_config)

    optimized_panel = {
        "top_disruptive_panel": disruptive_panel,
        "top_tolerated_panel": tolerated_panel,
        "allele_discrimination_panel": discriminatory_panel,
        "anchor_behavior_panel": anchor_panel,
        "balanced_exploration_panel": balanced_panel,
    }.get(panel_config.ranking_goal, balanced_panel)

    combined = pd.concat(
        [disruptive_panel, tolerated_panel, discriminatory_panel, anchor_panel, balanced_panel],
        ignore_index=True,
    ).drop_duplicates(subset=["panel_id", "variant_id"], keep="first")
    coverage = _panel_coverage_summary(combined)
    report = _panel_report(coverage)
    return PanelDesignResult(
        optimized_panel_df=optimized_panel,
        panel_coverage_df=coverage,
        discriminatory_panel_df=discriminatory_panel,
        balanced_panel_df=balanced_panel,
        report_markdown=report,
    )


def _select_panel(
    priority_df: pd.DataFrame,
    mode_name: str,
    panel_id: str,
    panel_config: PanelDesignConfig,
) -> pd.DataFrame:
    subset = priority_df[priority_df["ranking_mode"] == mode_name].copy()
    if subset.empty:
        return pd.DataFrame()
    subset["priority_score"] = pd.to_numeric(subset["priority_score"], errors="coerce").fillna(0.0)
    subset["evidence_coverage_score"] = pd.to_numeric(subset["evidence_coverage_score"], errors="coerce").fillna(0.0)
    subset = subset[subset["evidence_coverage_score"] >= panel_config.require_min_evidence_coverage]
    if panel_config.penalize_high_uncertainty:
        penalty_map = {"low": 0.0, "moderate": 0.15, "high": 0.35, "insufficient_data": 0.5}
        subset["uncertainty_penalty"] = subset["uncertainty_flag"].map(penalty_map).fillna(0.25)
    else:
        subset["uncertainty_penalty"] = 0.0
    subset["selection_score"] = subset["priority_score"] - subset["uncertainty_penalty"]
    subset = subset.sort_values(["selection_score", "evidence_coverage_score"], ascending=[False, False])

    selected: list[dict[str, object]] = []
    position_counts: dict[object, int] = {}
    allele_counts: dict[object, int] = {}
    substitution_counts: dict[object, int] = {}

    for row in subset.to_dict(orient="records"):
        if len(selected) >= panel_config.max_panel_size:
            break
        position = row.get("mutated_position")
        allele = row.get("allele_name")
        substitution = row.get("mut_residue")
        if position_counts.get(position, 0) >= panel_config.diversity_constraints.max_variants_per_position:
            continue
        if allele_counts.get(allele, 0) >= panel_config.diversity_constraints.max_variants_per_allele:
            continue
        if substitution_counts.get(substitution, 0) >= panel_config.diversity_constraints.max_variants_per_substitution:
            continue
        redundancy_penalty = _redundancy_penalty(selected, row, panel_config.redundancy_features)
        selected.append(
            {
                "panel_id": panel_id,
                "ranking_goal": mode_name,
                "variant_id": row.get("variant_id"),
                "allele_name": allele,
                "mutant_peptide": row.get("mutant_peptide"),
                "mutated_position": position,
                "substitution": substitution,
                "selection_reason": f"Selected from {mode_name} with diversity constraints.",
                "supporting_metrics_serialized": row.get("evidence_components_serialized"),
                "redundancy_penalty": redundancy_penalty,
                "evidence_coverage_score": row.get("evidence_coverage_score"),
                "uncertainty_level": row.get("uncertainty_flag"),
                "mean_priority_score": row.get("priority_score"),
            }
        )
        position_counts[position] = position_counts.get(position, 0) + 1
        allele_counts[allele] = allele_counts.get(allele, 0) + 1
        substitution_counts[substitution] = substitution_counts.get(substitution, 0) + 1
    return pd.DataFrame(selected)


def _redundancy_penalty(selected: list[dict[str, object]], row: dict[str, object], redundancy_features: list[str]) -> float:
    penalty = 0.0
    for selected_row in selected:
        for feature in redundancy_features:
            if selected_row.get(feature) == row.get(feature):
                penalty += 0.1
    return penalty


def _panel_coverage_summary(panel_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    summary = (
        panel_df.groupby("panel_id", dropna=False)
        .agg(
            num_variants=("variant_id", "nunique"),
            num_alleles_covered=("allele_name", "nunique"),
            num_positions_covered=("mutated_position", "nunique"),
            num_substitutions_covered=("substitution", "nunique"),
            mean_priority_score=("mean_priority_score", "mean"),
            mean_evidence_coverage=("evidence_coverage_score", "mean"),
        )
        .reset_index()
    )
    summary["diversity_score"] = (
        summary["num_alleles_covered"] + summary["num_positions_covered"] + summary["num_substitutions_covered"]
    ) / summary["num_variants"].clip(lower=1)
    summary["design_notes"] = "Greedy score-plus-diversity panel selection with explicit per-feature quotas."
    return summary


def _panel_report(coverage_df: pd.DataFrame) -> str:
    lines = ["# Panel Design Report", ""]
    if coverage_df.empty:
        lines.append("No panel rows were selected under the current constraints.")
        return "\n".join(lines)
    for row in coverage_df.to_dict(orient="records"):
        lines.append(
            f"- `{row['panel_id']}` selected {row['num_variants']} variants across {row['num_alleles_covered']} allele(s) and {row['num_positions_covered']} position(s)."
        )
    return "\n".join(lines)
