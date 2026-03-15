from __future__ import annotations

import pandas as pd


def build_ranking_feature_table(
    summary_df: pd.DataFrame,
    fingerprint_df: pd.DataFrame,
    allele_position_df: pd.DataFrame,
    region_contacts_df: pd.DataFrame,
    case_studies: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    feature_df = summary_df.copy()
    if not fingerprint_df.empty:
        fingerprint_cols = [
            "variant_id",
            "mutated_position_contact_pattern_change",
            "lost_anchor_contacts",
            "gained_anchor_contacts",
            "fingerprint_status",
        ]
        feature_df = feature_df.merge(
            fingerprint_df[[column for column in fingerprint_cols if column in fingerprint_df.columns]],
            on="variant_id",
            how="left",
        )

    for column in [
        "delta_total_contacts_vs_wt",
        "delta_mean_min_distance_vs_wt",
        "delta_confidence_vs_wt",
        "delta_mean_plddt_vs_wt",
        "delta_pae_vs_wt",
        "delta_contacts_at_mutated_position_vs_wt",
        "delta_contacts_at_anchor_positions_vs_wt",
        "gained_contacting_mhc_residues_count_vs_wt",
        "lost_contacting_mhc_residues_count_vs_wt",
    ]:
        if column not in feature_df.columns:
            feature_df[column] = pd.NA

    feature_df["anchor_disruption_flag"] = pd.to_numeric(
        feature_df.get("delta_contacts_at_anchor_positions_vs_wt"),
        errors="coerce",
    ).lt(0).astype(float)
    feature_df["absolute_contact_change"] = pd.to_numeric(
        feature_df.get("delta_total_contacts_vs_wt"),
        errors="coerce",
    ).abs()
    feature_df["structural_data_present"] = feature_df.get("total_peptide_mhc_contacts", pd.Series(dtype=float)).notna().astype(float)
    feature_df["wt_reference_present"] = feature_df.get("delta_confidence_vs_wt", pd.Series(dtype=float)).notna().astype(float)
    feature_df["chain_mapping_confident"] = feature_df.get("chain_mapping_confidence", pd.Series(dtype=object)).isin(
        ["high", "medium"]
    ).astype(float)
    feature_df["prediction_complete"] = feature_df.get("prediction_present", pd.Series(dtype=object)).fillna(False).astype(bool).astype(float)
    feature_df["evidence_coverage_proxy"] = _compute_coverage_proxy(feature_df)
    feature_df["cross_allele_contact_divergence"] = _cross_allele_divergence(
        feature_df,
        value_column="delta_total_contacts_vs_wt",
    )
    feature_df["cross_allele_rank_divergence"] = _cross_allele_rank_divergence(feature_df)
    feature_df["pocket_region_disruption_flag"] = _pocket_region_disruption(region_contacts_df, feature_df)
    feature_df["case_study_relevance_flag"] = _case_study_relevance(feature_df, case_studies)
    feature_df["case_study_labels"] = _case_study_labels(feature_df, case_studies)
    return feature_df


def _compute_coverage_proxy(feature_df: pd.DataFrame) -> pd.Series:
    relevant = [
        "delta_total_contacts_vs_wt",
        "delta_mean_min_distance_vs_wt",
        "delta_confidence_vs_wt",
        "delta_contacts_at_mutated_position_vs_wt",
        "delta_contacts_at_anchor_positions_vs_wt",
    ]
    available = pd.DataFrame({column: feature_df[column].notna() for column in relevant if column in feature_df.columns})
    if available.empty:
        return pd.Series([0.0] * len(feature_df), index=feature_df.index)
    return available.mean(axis=1)


def _cross_allele_divergence(feature_df: pd.DataFrame, value_column: str) -> pd.Series:
    if value_column not in feature_df.columns:
        return pd.Series([pd.NA] * len(feature_df), index=feature_df.index)
    working = feature_df[["variant_id", "local_variant_id", "peptide_id", value_column]].copy()
    working[value_column] = pd.to_numeric(working[value_column], errors="coerce")
    grouped = (
        working.groupby(["local_variant_id", "peptide_id"], dropna=False)[value_column]
        .agg(lambda values: values.max() - values.min() if values.notna().any() else pd.NA)
        .reset_index(name="divergence")
    )
    merged = working.merge(grouped, on=["local_variant_id", "peptide_id"], how="left")
    return merged.set_index("variant_id").reindex(feature_df["variant_id"])["divergence"].reset_index(drop=True)


def _cross_allele_rank_divergence(feature_df: pd.DataFrame) -> pd.Series:
    working = feature_df[["variant_id", "local_variant_id", "peptide_id"]].copy()
    proxy = (
        -pd.to_numeric(feature_df.get("delta_total_contacts_vs_wt"), errors="coerce").fillna(0.0)
        + pd.to_numeric(feature_df.get("delta_mean_min_distance_vs_wt"), errors="coerce").fillna(0.0)
    )
    working["proxy_score"] = proxy
    divergence = (
        working.groupby(["local_variant_id", "peptide_id"], dropna=False)["proxy_score"]
        .agg(lambda values: float(values.max() - values.min()) if len(values) > 0 else pd.NA)
        .reset_index(name="rank_divergence")
    )
    merged = working.merge(divergence, on=["local_variant_id", "peptide_id"], how="left")
    return merged.set_index("variant_id").reindex(feature_df["variant_id"])["rank_divergence"].reset_index(drop=True)


def _pocket_region_disruption(region_contacts_df: pd.DataFrame, feature_df: pd.DataFrame) -> pd.Series:
    if region_contacts_df.empty or "variant_id" not in region_contacts_df.columns:
        return pd.Series([0.0] * len(feature_df), index=feature_df.index)
    counts = region_contacts_df.groupby("variant_id", dropna=False)["pocket_region"].nunique().to_dict()
    return feature_df["variant_id"].map(lambda value: 1.0 if counts.get(value, 0) > 0 else 0.0)


def _case_study_relevance(feature_df: pd.DataFrame, case_studies: list[object] | None) -> pd.Series:
    if not case_studies:
        return pd.Series([0.0] * len(feature_df), index=feature_df.index)
    labels = _case_study_labels(feature_df, case_studies)
    return labels.apply(lambda value: 1.0 if value else 0.0)


def _case_study_labels(feature_df: pd.DataFrame, case_studies: list[object] | None) -> pd.Series:
    if not case_studies:
        return pd.Series([""] * len(feature_df), index=feature_df.index)
    labels = []
    for row in feature_df.to_dict(orient="records"):
        hits = []
        for case in case_studies:
            alleles = _case_value(case, "alleles") or []
            positions = set(_case_value(case, "mutation_positions") or [])
            substitutions = set(_case_value(case, "substitutions") or [])
            variants = set(_case_value(case, "variants") or [])
            mutated_position = pd.to_numeric(pd.Series([row.get("mutated_position")]), errors="coerce").iloc[0]
            if alleles and row.get("allele_name") not in alleles:
                continue
            if positions and (pd.isna(mutated_position) or int(mutated_position) not in positions):
                continue
            if substitutions and str(row.get("mut_residue") or "") not in substitutions:
                continue
            if variants and str(row.get("variant_id")) not in variants:
                continue
            hits.append(str(_case_value(case, "case_id", "")))
        labels.append(";".join(sorted(set(hits))))
    return pd.Series(labels, index=feature_df.index)


def _case_value(case: object, field: str, default: object = None) -> object:
    if isinstance(case, dict):
        return case.get(field, default)
    return getattr(case, field, default)
