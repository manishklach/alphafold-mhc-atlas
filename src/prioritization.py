from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PrioritizationConfig, RankingModeConfig


@dataclass(frozen=True)
class PrioritizationResult:
    variant_priority_df: pd.DataFrame
    evidence_df: pd.DataFrame
    top_tables: dict[str, pd.DataFrame]


def run_prioritization(
    feature_df: pd.DataFrame,
    uncertainty_df: pd.DataFrame,
    config: PrioritizationConfig,
) -> PrioritizationResult:
    if not config.enabled or feature_df.empty:
        empty = pd.DataFrame()
        return PrioritizationResult(empty, empty, {})

    priority_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    top_tables: dict[str, pd.DataFrame] = {}

    for mode_name, mode_config in config.ranking_modes.items():
        if not mode_config.enabled:
            continue
        mode_rows, mode_evidence = _score_mode(feature_df, uncertainty_df, mode_name, mode_config)
        priority_rows.extend(mode_rows)
        evidence_rows.extend(mode_evidence)

    priority_df = pd.DataFrame(priority_rows)
    evidence_df = pd.DataFrame(evidence_rows)
    if priority_df.empty:
        return PrioritizationResult(priority_df, evidence_df, {})

    priority_df = priority_df.sort_values(["ranking_mode", "priority_rank", "variant_id"]).reset_index(drop=True)
    top_tables = {
        "top_disruptive_mutations.csv": _top_table(priority_df, "disruptive_mutations", config.default_top_k),
        "top_tolerated_mutations.csv": _top_table(priority_df, "tolerated_mutations", config.default_top_k),
        "top_discriminating_mutations.csv": _top_table(priority_df, "allele_discriminating_mutations", config.default_top_k),
        "top_anchor_sensitive_mutations.csv": _top_table(priority_df, "anchor_sensitive_mutations", config.default_top_k),
    }
    return PrioritizationResult(priority_df, evidence_df, top_tables)


def _score_mode(
    feature_df: pd.DataFrame,
    uncertainty_df: pd.DataFrame,
    mode_name: str,
    mode_config: RankingModeConfig,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    working = feature_df.copy()
    if mode_config.require_structural_support and "structural_data_present" in working.columns:
        working = working[working["structural_data_present"] > 0]
    if working.empty:
        return [], []

    normalized_map: dict[str, pd.Series] = {}
    for feature in mode_config.features:
        series = pd.to_numeric(working.get(feature.name), errors="coerce")
        normalized_map[feature.name] = _normalize_series(series) if mode_config.normalize_features else series

    priority_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    for _, row in working.iterrows():
        contributions = []
        score = 0.0
        for feature in mode_config.features:
            value = row.get(feature.name)
            normalized_value = normalized_map[feature.name].loc[row.name] if feature.name in normalized_map else pd.NA
            status = "ok" if not pd.isna(value) else "missing"
            contribution = 0.0 if pd.isna(normalized_value) else float(normalized_value) * feature.weight
            score += contribution
            evidence_rows.append(
                {
                    "variant_id": row["variant_id"],
                    "ranking_mode": mode_name,
                    "evidence_name": feature.name,
                    "evidence_value": value,
                    "evidence_direction": _direction_label(feature.weight),
                    "evidence_weight": feature.weight,
                    "evidence_status": status,
                    "notes": "Missing values contribute zero to the decomposed score." if status == "missing" else "",
                }
            )
            if status == "ok":
                contributions.append(f"{feature.name}={_format_value(value)}@{feature.weight:.2f}")

        uncertainty_row = _lookup_uncertainty(uncertainty_df, row["variant_id"], mode_name)
        priority_rows.append(
            {
                "variant_id": row["variant_id"],
                "allele_name": row.get("allele_name"),
                "mutant_peptide": row.get("mutant_peptide"),
                "mutated_position": row.get("mutated_position"),
                "wt_residue": row.get("wt_residue"),
                "mut_residue": row.get("mut_residue"),
                "ranking_mode": mode_name,
                "priority_score": score,
                "evidence_components_serialized": ";".join(contributions),
                "evidence_coverage_score": uncertainty_row.get("evidence_coverage_score"),
                "structural_support_status": "available" if bool(row.get("structural_data_present", 0.0)) else "limited",
                "uncertainty_flag": uncertainty_row.get("uncertainty_level"),
                "prioritization_notes": _prioritization_notes(mode_name, row, uncertainty_row),
            }
        )

    mode_df = pd.DataFrame(priority_rows)
    if mode_df.empty:
        return [], evidence_rows
    mode_df = mode_df.sort_values(
        by=["priority_score", "evidence_coverage_score", "variant_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    mode_df["priority_rank"] = range(1, len(mode_df) + 1)
    return mode_df.to_dict(orient="records"), evidence_rows


def _normalize_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series([pd.NA] * len(series), index=series.index)
    std = valid.std()
    if pd.isna(std) or std == 0:
        centered = numeric - valid.mean()
        return centered.fillna(0.0)
    return (numeric - valid.mean()) / std


def _lookup_uncertainty(uncertainty_df: pd.DataFrame, variant_id: str, mode_name: str) -> dict[str, object]:
    if uncertainty_df.empty:
        return {}
    matches = uncertainty_df[
        (uncertainty_df["variant_id"] == variant_id) & (uncertainty_df["ranking_mode"] == mode_name)
    ]
    if matches.empty:
        return {}
    return matches.iloc[0].to_dict()


def _direction_label(weight: float) -> str:
    if weight > 0:
        return "higher_increases_priority"
    if weight < 0:
        return "lower_increases_priority"
    return "neutral"


def _format_value(value: object) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _prioritization_notes(mode_name: str, row: pd.Series, uncertainty_row: dict[str, object]) -> str:
    notes = [f"Transparent ranking mode: {mode_name}."]
    if uncertainty_row.get("uncertainty_level") in {"high", "insufficient_data"}:
        notes.append("Evidence support is limited; treat ranking as exploratory.")
    if not bool(row.get("structural_data_present", 0.0)):
        notes.append("Structural support is absent or incomplete.")
    return " ".join(notes)


def _top_table(priority_df: pd.DataFrame, mode_name: str, top_k: int) -> pd.DataFrame:
    filtered = priority_df[priority_df["ranking_mode"] == mode_name].copy()
    if filtered.empty:
        return pd.DataFrame()
    return filtered.head(top_k).reset_index(drop=True)
