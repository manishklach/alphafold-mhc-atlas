from __future__ import annotations

import pandas as pd

from .config import RankingModeConfig, UncertaintyConfig


def build_priority_uncertainty_table(
    feature_df: pd.DataFrame,
    ranking_modes: dict[str, RankingModeConfig],
    config: UncertaintyConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for mode_name, mode_config in ranking_modes.items():
        if not mode_config.enabled:
            continue
        for row in feature_df.to_dict(orient="records"):
            feature_names = [feature.name for feature in mode_config.features]
            available = sum(1 for name in feature_names if not pd.isna(row.get(name)))
            missing = len(feature_names) - available
            structural_data_present = bool(row.get("structural_data_present", 0.0))
            wt_reference_present = not pd.isna(row.get("delta_confidence_vs_wt"))
            chain_mapping_confident = bool(row.get("chain_mapping_confident", 0.0))
            prediction_complete = bool(row.get("prediction_complete", 0.0))
            coverage = available / max(1, len(feature_names))
            reasons = []
            if missing > 0:
                reasons.append("missing_features")
            if not structural_data_present:
                reasons.append("no_structural_data")
            if not wt_reference_present:
                reasons.append("no_wt_reference")
            if config.penalize_unconfident_chain_mapping and not chain_mapping_confident:
                reasons.append("unconfident_chain_mapping")
            if not prediction_complete:
                reasons.append("prediction_incomplete")
            rows.append(
                {
                    "variant_id": row.get("variant_id"),
                    "ranking_mode": mode_name,
                    "evidence_coverage_score": coverage,
                    "num_supporting_features": available,
                    "num_missing_features": missing,
                    "structural_data_present": structural_data_present,
                    "wt_reference_present": wt_reference_present,
                    "chain_mapping_confident": chain_mapping_confident,
                    "prediction_complete": prediction_complete,
                    "uncertainty_level": _uncertainty_level(coverage, reasons),
                    "uncertainty_reasons_serialized": ";".join(reasons),
                }
            )
    uncertainty_df = pd.DataFrame(rows)
    if uncertainty_df.empty:
        return uncertainty_df, pd.DataFrame()
    coverage_summary = (
        uncertainty_df.groupby("ranking_mode", dropna=False)
        .agg(
            mean_evidence_coverage=("evidence_coverage_score", "mean"),
            mean_supporting_features=("num_supporting_features", "mean"),
            fraction_low_uncertainty=("uncertainty_level", lambda values: (values == "low").mean()),
            fraction_insufficient_data=("uncertainty_level", lambda values: (values == "insufficient_data").mean()),
        )
        .reset_index()
    )
    return uncertainty_df, coverage_summary


def _uncertainty_level(coverage: float, reasons: list[str]) -> str:
    if coverage < 0.25:
        return "insufficient_data"
    if coverage < 0.5 or "no_structural_data" in reasons:
        return "high"
    if coverage < 0.75 or "prediction_incomplete" in reasons or "unconfident_chain_mapping" in reasons:
        return "moderate"
    return "low"
