from __future__ import annotations

import pandas as pd


def build_variant_summary(records: list[dict], baseline_variant_id: str = "WT") -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df

    if "best_available_confidence" not in df.columns:
        df["best_available_confidence"] = pd.NA
    if "best_available_confidence_source" not in df.columns:
        df["best_available_confidence_source"] = pd.NA
    if "ranking_confidence" not in df.columns:
        df["ranking_confidence"] = pd.NA
    if "mean_plddt" not in df.columns:
        df["mean_plddt"] = pd.NA
    if "pae_mean" not in df.columns:
        df["pae_mean"] = pd.NA

    df["confidence_available"] = df["best_available_confidence"].notna()
    df["primary_score"] = df["best_available_confidence"]
    df["score_source"] = df["best_available_confidence_source"].fillna("unavailable")
    df["structural_metric_placeholder"] = pd.NA

    if {"allele_name", "peptide_id"}.issubset(df.columns):
        context_columns = df[["variant_id", "allele_name", "peptide_id"]].copy()
        grouped = df.groupby(["allele_name", "peptide_id"], dropna=False, group_keys=False)
        df = grouped.apply(lambda group: _apply_group_baseline(group, baseline_variant_id)).reset_index(drop=True)
        if "allele_name" not in df.columns or "peptide_id" not in df.columns:
            df = df.merge(context_columns, on="variant_id", how="left")
    else:
        baseline_row = _select_baseline_row(df, baseline_variant_id)
        if baseline_row is not None:
            df["delta_confidence_vs_wt"] = df["ranking_confidence"].apply(
                lambda value: _safe_delta(value, baseline_row.get("ranking_confidence"))
            )
            df["delta_mean_plddt_vs_wt"] = df["mean_plddt"].apply(
                lambda value: _safe_delta(value, baseline_row.get("mean_plddt"))
            )
            df["delta_pae_vs_wt"] = df["pae_mean"].apply(
                lambda value: _safe_delta(value, baseline_row.get("pae_mean"))
            )
        else:
            df["delta_confidence_vs_wt"] = pd.NA
            df["delta_mean_plddt_vs_wt"] = pd.NA
            df["delta_pae_vs_wt"] = pd.NA

    return df


def build_confidence_ranking(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df.copy()
    ranking_df = summary_df.sort_values(
        by=["primary_score", "mean_plddt", "variant_id"],
        ascending=[False, False, True],
        na_position="last",
    )
    return ranking_df.reset_index(drop=True)


def build_position_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    mutant_df = summary_df[summary_df["mutated_position"].notna()].copy()
    if mutant_df.empty:
        return pd.DataFrame()

    agg_map = {
        "variant_count": ("variant_id", "count"),
        "avg_primary_score": ("primary_score", "mean"),
        "avg_ranking_confidence": ("ranking_confidence", "mean"),
        "avg_mean_plddt": ("mean_plddt", "mean"),
        "avg_delta_confidence_vs_wt": ("delta_confidence_vs_wt", "mean"),
        "avg_delta_mean_plddt_vs_wt": ("delta_mean_plddt_vs_wt", "mean"),
        "avg_delta_pae_vs_wt": ("delta_pae_vs_wt", "mean"),
        "prediction_present_fraction": ("prediction_present", "mean"),
    }
    structural_columns = {
        "avg_total_peptide_mhc_contacts": "total_peptide_mhc_contacts",
        "avg_mean_min_distance_to_mhc": "mean_min_distance_to_mhc",
        "avg_delta_total_contacts_vs_wt": "delta_total_contacts_vs_wt",
        "avg_delta_mean_min_distance_vs_wt": "delta_mean_min_distance_vs_wt",
        "avg_delta_contacts_at_mutated_position_vs_wt": "delta_contacts_at_mutated_position_vs_wt",
    }
    for output_name, input_name in structural_columns.items():
        if input_name in mutant_df.columns:
            agg_map[output_name] = (input_name, "mean")

    grouped = mutant_df.groupby("mutated_position", dropna=True).agg(**agg_map).reset_index()
    return grouped


def build_substitution_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    mutant_df = summary_df[
        summary_df["mutated_position"].notna() & summary_df["mut_residue"].notna()
    ].copy()
    if mutant_df.empty:
        return pd.DataFrame()

    agg_map = {
        "variant_count": ("variant_id", "count"),
        "avg_primary_score": ("primary_score", "mean"),
        "avg_delta_confidence_vs_wt": ("delta_confidence_vs_wt", "mean"),
        "avg_delta_mean_plddt_vs_wt": ("delta_mean_plddt_vs_wt", "mean"),
        "avg_delta_pae_vs_wt": ("delta_pae_vs_wt", "mean"),
    }
    for output_name, input_name in {
        "avg_delta_total_contacts_vs_wt": "delta_total_contacts_vs_wt",
        "avg_delta_mean_min_distance_vs_wt": "delta_mean_min_distance_vs_wt",
        "avg_delta_contacts_at_mutated_position_vs_wt": "delta_contacts_at_mutated_position_vs_wt",
    }.items():
        if input_name in mutant_df.columns:
            agg_map[output_name] = (input_name, "mean")

    grouped = mutant_df.groupby(["mutated_position", "mut_residue"], dropna=True).agg(**agg_map).reset_index()
    return grouped


def build_substitution_matrix(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    mutant_df = summary_df[
        summary_df["mutated_position"].notna() & summary_df["mut_residue"].notna() & summary_df["primary_score"].notna()
    ].copy()
    if mutant_df.empty:
        return pd.DataFrame()

    heatmap_df = mutant_df.pivot_table(
        index="mutated_position",
        columns="mut_residue",
        values="primary_score",
        aggfunc="mean",
    )
    return heatmap_df.sort_index()


def _select_baseline_row(df: pd.DataFrame, baseline_variant_id: str) -> pd.Series | None:
    matches = df[df.get("local_variant_id", df["variant_id"]) == baseline_variant_id]
    if matches.empty:
        matches = df[df["variant_id"] == baseline_variant_id]
    if matches.empty:
        return None
    return matches.iloc[0]


def _apply_group_baseline(group: pd.DataFrame, baseline_variant_id: str) -> pd.DataFrame:
    baseline_row = _select_baseline_row(group, baseline_variant_id)
    if baseline_row is None:
        group["delta_confidence_vs_wt"] = pd.NA
        group["delta_mean_plddt_vs_wt"] = pd.NA
        group["delta_pae_vs_wt"] = pd.NA
        return group
    group["delta_confidence_vs_wt"] = group["ranking_confidence"].apply(
        lambda value: _safe_delta(value, baseline_row.get("ranking_confidence"))
    )
    group["delta_mean_plddt_vs_wt"] = group["mean_plddt"].apply(
        lambda value: _safe_delta(value, baseline_row.get("mean_plddt"))
    )
    group["delta_pae_vs_wt"] = group["pae_mean"].apply(
        lambda value: _safe_delta(value, baseline_row.get("pae_mean"))
    )
    return group


def _safe_delta(value: object, baseline: object) -> float | pd.NA:
    if pd.isna(value) or pd.isna(baseline):
        return pd.NA
    return float(value) - float(baseline)
