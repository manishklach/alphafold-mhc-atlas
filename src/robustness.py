from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PrioritizationConfig, RobustnessConfig
from .prioritization import run_prioritization


@dataclass(frozen=True)
class RobustnessResult:
    robustness_summary_df: pd.DataFrame
    threshold_sensitivity_df: pd.DataFrame
    ranking_stability_df: pd.DataFrame
    replicate_consistency_df: pd.DataFrame
    report_markdown: str


def run_robustness_analysis(
    feature_df: pd.DataFrame,
    uncertainty_df: pd.DataFrame,
    baseline_priority_df: pd.DataFrame,
    prioritization_config: PrioritizationConfig,
    robustness_config: RobustnessConfig,
) -> RobustnessResult:
    empty = RobustnessResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "# Robustness\n\nDisabled.\n")
    if not robustness_config.enabled or baseline_priority_df.empty:
        return empty

    baseline_ranks = baseline_priority_df[["ranking_mode", "variant_id", "priority_rank"]].rename(
        columns={"priority_rank": "baseline_rank"}
    )

    threshold_rows = [
        {
            "alternative_run_id": f"threshold_{threshold}",
            "contact_distance_threshold": threshold,
            "status": "skipped",
            "notes": "Contact-threshold sensitivity requires recomputing structural contacts; this run records configuration-only sensitivity.",
        }
        for threshold in robustness_config.contact_distance_thresholds
    ]

    alt_runs: list[tuple[str, PrioritizationConfig]] = []
    for mode_name, mode_config in prioritization_config.ranking_modes.items():
        if not mode_config.enabled or not mode_config.features:
            continue
        feature = mode_config.features[0]
        plus_config = _perturb_weight(prioritization_config, mode_name, feature.name, 1 + robustness_config.weight_perturbation_fraction)
        minus_config = _perturb_weight(prioritization_config, mode_name, feature.name, max(0.0, 1 - robustness_config.weight_perturbation_fraction))
        alt_runs.append((f"{mode_name}__weight_up_{feature.name}", plus_config))
        alt_runs.append((f"{mode_name}__weight_down_{feature.name}", minus_config))
        if robustness_config.missing_feature_drop_tests:
            drop_config = _drop_feature(prioritization_config, mode_name, feature.name)
            alt_runs.append((f"{mode_name}__drop_{feature.name}", drop_config))

    stability_rows: list[dict[str, object]] = []
    top_k_values = robustness_config.compare_top_k
    for run_id, config in alt_runs:
        alt_result = run_prioritization(feature_df, uncertainty_df, config)
        if alt_result.variant_priority_df.empty:
            continue
        alt_df = alt_result.variant_priority_df[["ranking_mode", "variant_id", "priority_rank"]].rename(
            columns={"priority_rank": "alternative_rank"}
        )
        merged = baseline_ranks.merge(alt_df, on=["ranking_mode", "variant_id"], how="left")
        for row in merged.to_dict(orient="records"):
            flags = {
                f"top_{k}": bool(row.get("baseline_rank", 10**9) <= k and row.get("alternative_rank", 10**9) <= k)
                for k in top_k_values
            }
            stability_rows.append(
                {
                    "ranking_mode": row["ranking_mode"],
                    "variant_id": row["variant_id"],
                    "baseline_rank": row["baseline_rank"],
                    "alternative_run_id": run_id,
                    "alternative_rank": row.get("alternative_rank"),
                    "rank_shift": _rank_shift(row["baseline_rank"], row.get("alternative_rank")),
                    "remained_in_top_k_flags": ";".join(
                        f"{key}={str(value).lower()}" for key, value in flags.items()
                    ),
                    "stability_notes": "Feature weighting perturbation or feature-drop comparison.",
                }
            )

    ranking_stability_df = pd.DataFrame(stability_rows)
    robustness_summary_df = (
        ranking_stability_df.groupby("ranking_mode", dropna=False)
        .agg(
            mean_abs_rank_shift=("rank_shift", lambda values: pd.to_numeric(values, errors="coerce").abs().mean()),
            max_abs_rank_shift=("rank_shift", lambda values: pd.to_numeric(values, errors="coerce").abs().max()),
            num_alternative_runs=("alternative_run_id", "nunique"),
        )
        .reset_index()
        if not ranking_stability_df.empty
        else pd.DataFrame()
    )
    replicate_consistency_df = pd.DataFrame(
        [
            {
                "status": "not_available" if robustness_config.replicate_consistency else "skipped",
                "notes": "Multiple explicit replicate prediction sets were not detected in the current pipeline inputs.",
            }
        ]
    )
    report = _build_robustness_report(robustness_summary_df, threshold_rows, ranking_stability_df)
    return RobustnessResult(
        robustness_summary_df=robustness_summary_df,
        threshold_sensitivity_df=pd.DataFrame(threshold_rows),
        ranking_stability_df=ranking_stability_df,
        replicate_consistency_df=replicate_consistency_df,
        report_markdown=report,
    )


def _perturb_weight(config: PrioritizationConfig, mode_name: str, feature_name: str, factor: float) -> PrioritizationConfig:
    updated_modes = {}
    for name, mode in config.ranking_modes.items():
        if name != mode_name:
            updated_modes[name] = mode
            continue
        updated_features = []
        for feature in mode.features:
            weight = feature.weight * factor if feature.name == feature_name else feature.weight
            updated_features.append(type(feature)(name=feature.name, weight=weight))
        updated_modes[name] = type(mode)(
            enabled=mode.enabled,
            normalize_features=mode.normalize_features,
            require_structural_support=mode.require_structural_support,
            features=updated_features,
        )
    return type(config)(enabled=config.enabled, default_top_k=config.default_top_k, ranking_modes=updated_modes)


def _drop_feature(config: PrioritizationConfig, mode_name: str, feature_name: str) -> PrioritizationConfig:
    updated_modes = {}
    for name, mode in config.ranking_modes.items():
        if name != mode_name:
            updated_modes[name] = mode
            continue
        remaining = [feature for feature in mode.features if feature.name != feature_name]
        updated_modes[name] = type(mode)(
            enabled=mode.enabled,
            normalize_features=mode.normalize_features,
            require_structural_support=mode.require_structural_support,
            features=remaining or mode.features,
        )
    return type(config)(enabled=config.enabled, default_top_k=config.default_top_k, ranking_modes=updated_modes)


def _rank_shift(baseline_rank: object, alt_rank: object) -> float | pd.NA:
    if pd.isna(alt_rank):
        return pd.NA
    return float(alt_rank) - float(baseline_rank)


def _build_robustness_report(
    robustness_summary_df: pd.DataFrame,
    threshold_rows: list[dict[str, object]],
    ranking_stability_df: pd.DataFrame,
) -> str:
    lines = ["# Conclusion Stability Report", ""]
    if robustness_summary_df.empty:
        lines.append("No alternative ranking runs were available for robustness analysis.")
    else:
        for row in robustness_summary_df.to_dict(orient="records"):
            lines.append(
                f"- `{row['ranking_mode']}` mean absolute rank shift: {row['mean_abs_rank_shift']}. Max shift: {row['max_abs_rank_shift']}."
            )
    lines.extend(["", "## Threshold Sensitivity", ""])
    for row in threshold_rows:
        lines.append(f"- {row['alternative_run_id']}: {row['status']} ({row['notes']})")
    if not ranking_stability_df.empty:
        fragile = ranking_stability_df[pd.to_numeric(ranking_stability_df["rank_shift"], errors="coerce").abs() > 5]
        lines.extend(["", "## Fragile Conclusions", ""])
        if fragile.empty:
            lines.append("No variants showed large rank shifts in the current alternative runs.")
        else:
            for row in fragile.head(10).to_dict(orient="records"):
                lines.append(f"- `{row['variant_id']}` shifted by {row['rank_shift']} in `{row['alternative_run_id']}`.")
    return "\n".join(lines)
