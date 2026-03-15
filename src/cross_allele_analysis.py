from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import CrossAlleleAnalysisConfig


@dataclass(frozen=True)
class CrossAlleleResult:
    ran: bool
    notes: str
    feature_table: pd.DataFrame
    allele_similarity_matrix: pd.DataFrame
    allele_tolerance_distance_matrix: pd.DataFrame
    allele_pocket_jaccard_matrix: pd.DataFrame
    pocket_overlap_residues: pd.DataFrame
    shared_contact_residues: pd.DataFrame
    allele_unique_contact_residues: pd.DataFrame
    cross_allele_summary: pd.DataFrame
    allele_comparison_summary: pd.DataFrame
    plot_paths: list[Path]


def run_cross_allele_analysis(
    allele_fingerprint_df: pd.DataFrame,
    pocket_signature_residue_df: pd.DataFrame,
    allele_position_df: pd.DataFrame,
    config: CrossAlleleAnalysisConfig,
    plot_dir: Path,
) -> CrossAlleleResult:
    empty = CrossAlleleResult(
        ran=False,
        notes="Cross-allele analysis skipped.",
        feature_table=pd.DataFrame(),
        allele_similarity_matrix=pd.DataFrame(),
        allele_tolerance_distance_matrix=pd.DataFrame(),
        allele_pocket_jaccard_matrix=pd.DataFrame(),
        pocket_overlap_residues=pd.DataFrame(),
        shared_contact_residues=pd.DataFrame(),
        allele_unique_contact_residues=pd.DataFrame(),
        cross_allele_summary=pd.DataFrame(),
        allele_comparison_summary=pd.DataFrame(),
        plot_paths=[],
    )
    if not config.enabled:
        return empty
    if allele_fingerprint_df.empty:
        return empty
    if allele_fingerprint_df["allele_name"].nunique() < config.require_min_alleles:
        return CrossAlleleResult(**{**empty.__dict__, "notes": "Not enough alleles for cross-allele analysis."})

    feature_table = build_cross_allele_feature_table(allele_fingerprint_df, pocket_signature_residue_df)
    tolerance_distance = _numeric_distance_matrix(
        allele_fingerprint_df,
        index_col="allele_name",
        config=config,
    )
    pocket_jaccard = build_pocket_jaccard_matrix(pocket_signature_residue_df)
    combined_similarity = _combine_similarity_matrices(tolerance_distance, pocket_jaccard)
    overlap_df, shared_df, unique_df = build_pocket_overlap_tables(pocket_signature_residue_df)
    cross_summary = build_cross_allele_summary(allele_fingerprint_df, pocket_signature_residue_df)
    comparison_summary = build_allele_comparison_summary(allele_position_df)
    plot_paths = _create_cross_allele_plots(
        tolerance_distance,
        pocket_jaccard,
        feature_table,
        comparison_summary,
        plot_dir,
    )
    return CrossAlleleResult(
        ran=True,
        notes="Cross-allele analysis completed.",
        feature_table=feature_table,
        allele_similarity_matrix=combined_similarity,
        allele_tolerance_distance_matrix=tolerance_distance,
        allele_pocket_jaccard_matrix=pocket_jaccard,
        pocket_overlap_residues=overlap_df,
        shared_contact_residues=shared_df,
        allele_unique_contact_residues=unique_df,
        cross_allele_summary=cross_summary,
        allele_comparison_summary=comparison_summary,
        plot_paths=plot_paths,
    )


def build_cross_allele_feature_table(
    allele_fingerprint_df: pd.DataFrame,
    pocket_signature_residue_df: pd.DataFrame,
) -> pd.DataFrame:
    if allele_fingerprint_df.empty:
        return pd.DataFrame()
    table = allele_fingerprint_df.copy()
    if not pocket_signature_residue_df.empty:
        pocket_summary = (
            pocket_signature_residue_df.groupby("allele_name", dropna=True)
            .agg(
                num_unique_contacting_residues=("mhc_residue_identifier", "nunique"),
                contact_density_score=("contact_frequency", "sum"),
                anchor_focus_score=("anchor_contact_frequency", "sum"),
            )
            .reset_index()
        )
        table = table.merge(pocket_summary, on="allele_name", how="left")
    return table


def build_pocket_jaccard_matrix(pocket_signature_residue_df: pd.DataFrame) -> pd.DataFrame:
    if pocket_signature_residue_df.empty:
        return pd.DataFrame()
    residue_sets = {
        allele: set(group["mhc_residue_identifier"].dropna())
        for allele, group in pocket_signature_residue_df.groupby("allele_name", dropna=True)
    }
    alleles = sorted(residue_sets)
    matrix = np.zeros((len(alleles), len(alleles)))
    for i, allele_a in enumerate(alleles):
        for j, allele_b in enumerate(alleles):
            union = residue_sets[allele_a] | residue_sets[allele_b]
            intersection = residue_sets[allele_a] & residue_sets[allele_b]
            matrix[i, j] = 1.0 if not union else len(intersection) / len(union)
    return pd.DataFrame(matrix, index=alleles, columns=alleles)


def build_pocket_overlap_tables(
    pocket_signature_residue_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if pocket_signature_residue_df.empty:
        empty = pd.DataFrame()
        return empty, empty, empty
    grouped = (
        pocket_signature_residue_df.groupby("mhc_residue_identifier", dropna=True)
        .agg(
            allele_count=("allele_name", "nunique"),
            alleles=("allele_name", lambda values: ";".join(sorted(set(values)))),
        )
        .reset_index()
    )
    shared = grouped[grouped["allele_count"] > 1].copy()
    unique_records = (
        pocket_signature_residue_df.groupby(["allele_name", "mhc_residue_identifier"], dropna=True)
        .size()
        .reset_index(name="count")
    )
    unique = unique_records.merge(grouped[["mhc_residue_identifier", "allele_count"]], on="mhc_residue_identifier")
    unique = unique[unique["allele_count"] == 1].drop(columns=["count", "allele_count"])
    return grouped, shared, unique


def build_cross_allele_summary(
    allele_fingerprint_df: pd.DataFrame,
    pocket_signature_residue_df: pd.DataFrame,
) -> pd.DataFrame:
    if allele_fingerprint_df.empty:
        return pd.DataFrame()
    summary = pd.DataFrame(
        [
            {
                "num_alleles": allele_fingerprint_df["allele_name"].nunique(),
                "mean_contact_density_score": pocket_signature_residue_df["contact_frequency"].mean()
                if not pocket_signature_residue_df.empty
                else pd.NA,
                "mean_abs_contact_change": allele_fingerprint_df["mean_abs_delta_total_contacts_vs_wt"].mean(),
            }
        ]
    )
    return summary


def build_allele_comparison_summary(allele_position_df: pd.DataFrame) -> pd.DataFrame:
    if allele_position_df.empty:
        return pd.DataFrame()
    if "avg_delta_total_contacts_vs_wt" not in allele_position_df.columns:
        return pd.DataFrame()
    working_df = allele_position_df.copy()
    working_df["avg_delta_total_contacts_vs_wt"] = pd.to_numeric(
        working_df["avg_delta_total_contacts_vs_wt"],
        errors="coerce",
    )
    grouped = (
        working_df.groupby("allele_name", dropna=True)
        .agg(
            most_sensitive_position=("avg_delta_total_contacts_vs_wt", _safe_series_min),
            mean_position_disruption=("avg_delta_total_contacts_vs_wt", "mean"),
        )
        .reset_index()
    )
    return grouped


def _numeric_distance_matrix(
    feature_df: pd.DataFrame,
    index_col: str,
    config: CrossAlleleAnalysisConfig,
) -> pd.DataFrame:
    numeric = feature_df.select_dtypes(include=["number"]).copy()
    numeric.index = feature_df[index_col]
    numeric = numeric.dropna(axis=1, how="all").fillna(0.0)
    matrix = numeric.to_numpy(dtype=float)
    if config.standardize_numeric_features and matrix.size:
        means = matrix.mean(axis=0)
        stds = matrix.std(axis=0)
        stds[stds == 0.0] = 1.0
        matrix = (matrix - means) / stds
    deltas = matrix[:, None, :] - matrix[None, :, :]
    distances = np.sqrt(np.sum(deltas * deltas, axis=2)) if matrix.size else np.zeros((len(numeric), len(numeric)))
    return pd.DataFrame(distances, index=numeric.index, columns=numeric.index)


def _combine_similarity_matrices(distance_df: pd.DataFrame, jaccard_df: pd.DataFrame) -> pd.DataFrame:
    if distance_df.empty:
        return pd.DataFrame()
    similarity = 1.0 / (1.0 + distance_df)
    if jaccard_df.empty:
        return similarity
    common = sorted(set(similarity.index) & set(jaccard_df.index))
    combined = similarity.copy()
    combined.loc[common, common] = (similarity.loc[common, common] + jaccard_df.loc[common, common]) / 2.0
    return combined


def _create_cross_allele_plots(
    tolerance_distance: pd.DataFrame,
    pocket_jaccard: pd.DataFrame,
    feature_table: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    plot_dir: Path,
) -> list[Path]:
    plot_paths: list[Path] = []
    if not tolerance_distance.empty:
        heatmap_path = plot_dir / "allele_similarity_heatmap.png"
        _plot_matrix(tolerance_distance, heatmap_path, "Allele tolerance distance matrix", "Distance")
        plot_paths.append(heatmap_path)

        projection_path = plot_dir / "allele_projection.png"
        _plot_projection(feature_table, projection_path)
        plot_paths.append(projection_path)

    if not pocket_jaccard.empty:
        pocket_path = plot_dir / "pocket_overlap_heatmap.png"
        _plot_matrix(pocket_jaccard, pocket_path, "Pocket overlap Jaccard matrix", "Jaccard")
        plot_paths.append(pocket_path)

    if not comparison_summary.empty:
        position_path = plot_dir / "position_sensitivity_by_allele.png"
        plt.figure(figsize=(6, 4))
        plt.bar(comparison_summary["allele_name"], comparison_summary["mean_position_disruption"], color="#4C78A8")
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Mean position disruption")
        plt.xlabel("Allele")
        plt.title("Position sensitivity by allele")
        plt.tight_layout()
        plt.savefig(position_path, dpi=150)
        plt.close()
        plot_paths.append(position_path)
    return plot_paths


def _plot_matrix(df: pd.DataFrame, output_path: Path, title: str, colorbar_label: str) -> None:
    plt.figure(figsize=(max(5, 0.7 * len(df.columns)), max(4, 0.5 * len(df.index))))
    plt.imshow(df.values, aspect="auto", cmap="viridis")
    plt.colorbar(label=colorbar_label)
    plt.xticks(range(len(df.columns)), df.columns, rotation=45, ha="right")
    plt.yticks(range(len(df.index)), df.index)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_projection(feature_table: pd.DataFrame, output_path: Path) -> None:
    if feature_table.empty:
        return
    numeric = feature_table.select_dtypes(include=["number"]).fillna(0.0)
    if numeric.shape[0] < 2 or numeric.shape[1] == 0:
        return
    centered = numeric.to_numpy(dtype=float) - numeric.to_numpy(dtype=float).mean(axis=0, keepdims=True)
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    components = vh[:2]
    projected = centered @ components.T if components.shape[0] >= 2 else np.column_stack([centered[:, 0], np.zeros(len(centered))])
    plt.figure(figsize=(6, 5))
    plt.scatter(projected[:, 0], projected[:, 1], color="#E45756")
    for allele_name, x, y in zip(feature_table["allele_name"], projected[:, 0], projected[:, 1]):
        plt.text(x, y, allele_name, fontsize=8)
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("Cross-allele feature projection")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _safe_series_min(values: pd.Series) -> float | pd.NA:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return pd.NA
    return float(numeric.min())
