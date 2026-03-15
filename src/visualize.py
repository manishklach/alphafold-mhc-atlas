from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def create_plots(
    summary_df: pd.DataFrame,
    position_df: pd.DataFrame,
    heatmap_df: pd.DataFrame,
    plot_dir: Path,
    peptide_position_df: pd.DataFrame | None = None,
    fingerprint_df: pd.DataFrame | None = None,
) -> list[Path]:
    plot_paths: list[Path] = []
    if summary_df.empty:
        return plot_paths

    variant_plot = plot_dir / "confidence_by_variant.png"
    _plot_confidence_by_variant(summary_df, variant_plot)
    plot_paths.append(variant_plot)

    if not position_df.empty:
        position_plot = plot_dir / "average_score_by_position.png"
        _plot_average_score_by_position(position_df, position_plot)
        plot_paths.append(position_plot)

    if not heatmap_df.empty and heatmap_df.shape[0] >= 1 and heatmap_df.shape[1] >= 2:
        heatmap_plot = plot_dir / "substitution_heatmap.png"
        _plot_substitution_heatmap(heatmap_df, heatmap_plot)
        plot_paths.append(heatmap_plot)

    if "total_peptide_mhc_contacts" in summary_df.columns and summary_df["total_peptide_mhc_contacts"].notna().any():
        contacts_plot = plot_dir / "total_contacts_by_variant.png"
        _plot_total_contacts_by_variant(summary_df, contacts_plot)
        plot_paths.append(contacts_plot)

    if "delta_total_contacts_vs_wt" in summary_df.columns and summary_df["delta_total_contacts_vs_wt"].notna().any():
        delta_plot = plot_dir / "delta_contacts_vs_wt.png"
        _plot_delta_contacts(summary_df, delta_plot)
        plot_paths.append(delta_plot)
        delta_mutant_plot = plot_dir / "delta_contacts_vs_wt_by_mutant.png"
        _plot_delta_contacts(summary_df, delta_mutant_plot)
        plot_paths.append(delta_mutant_plot)

    if peptide_position_df is not None and not peptide_position_df.empty:
        min_dist_plot = plot_dir / "mean_min_distance_by_peptide_position.png"
        _plot_mean_min_distance_by_position(peptide_position_df, min_dist_plot)
        plot_paths.append(min_dist_plot)

    if position_df is not None and not position_df.empty and "avg_delta_total_contacts_vs_wt" in position_df.columns:
        disruption_plot = plot_dir / "position_disruption_summary.png"
        _plot_position_disruption(position_df, disruption_plot)
        plot_paths.append(disruption_plot)

    if fingerprint_df is not None and not fingerprint_df.empty:
        feature_cols = [
            column
            for column in fingerprint_df.columns
            if column.startswith("delta_")
            or column in {"peptide_centroid_shift_vs_wt", "mutated_position_contact_pattern_change"}
        ]
        if feature_cols:
            fingerprint_heatmap = plot_dir / "fingerprint_feature_values.png"
            _plot_fingerprint_feature_values(fingerprint_df, feature_cols, fingerprint_heatmap)
            plot_paths.append(fingerprint_heatmap)

    coverage_plot = plot_dir / "coverage_overview.png"
    _plot_coverage_overview(summary_df, coverage_plot)
    plot_paths.append(coverage_plot)

    return plot_paths


def _plot_confidence_by_variant(summary_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = summary_df.copy()
    plot_df["display_score"] = pd.to_numeric(plot_df["primary_score"], errors="coerce").fillna(0.0)
    plot_df["display_label"] = _variant_labels(plot_df)

    plt.figure(figsize=(max(10, 0.4 * len(plot_df)), 4.5))
    plt.bar(plot_df["display_label"], plot_df["display_score"], color="#4C78A8")
    plt.xticks(rotation=75, ha="right", fontsize=8)
    plt.ylabel("Primary confidence score")
    plt.xlabel("Variant")
    plt.title("Confidence by mutant")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_average_score_by_position(position_df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(6, 4))
    y_values = pd.to_numeric(position_df["avg_primary_score"], errors="coerce").fillna(0.0)
    plt.bar(position_df["mutated_position"].astype(str), y_values, color="#F58518")
    plt.ylabel("Average primary score")
    plt.xlabel("Mutated position")
    plt.title("Average score by mutated position")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_substitution_heatmap(heatmap_df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(max(6, 0.6 * heatmap_df.shape[1]), max(4, 0.5 * heatmap_df.shape[0])))
    plt.imshow(heatmap_df.values, aspect="auto", cmap="viridis")
    plt.colorbar(label="Average primary score")
    plt.xticks(range(len(heatmap_df.columns)), heatmap_df.columns)
    plt.yticks(range(len(heatmap_df.index)), heatmap_df.index.astype(str))
    plt.xlabel("Substituted residue")
    plt.ylabel("Mutated position")
    plt.title("Amino-acid substitution heatmap")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_total_contacts_by_variant(summary_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = summary_df.copy()
    plot_df["value"] = pd.to_numeric(plot_df["total_peptide_mhc_contacts"], errors="coerce").fillna(0.0)
    plot_df["display_label"] = _variant_labels(plot_df)
    plt.figure(figsize=(max(10, 0.4 * len(plot_df)), 4.5))
    plt.bar(plot_df["display_label"], plot_df["value"], color="#54A24B")
    plt.xticks(rotation=75, ha="right", fontsize=8)
    plt.ylabel("Total peptide-MHC contacts")
    plt.xlabel("Variant")
    plt.title("Total contacts by variant")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_delta_contacts(summary_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = summary_df.copy()
    plot_df["value"] = pd.to_numeric(plot_df["delta_total_contacts_vs_wt"], errors="coerce").fillna(0.0)
    plot_df["display_label"] = _variant_labels(plot_df)
    plt.figure(figsize=(max(10, 0.4 * len(plot_df)), 4.5))
    plt.bar(plot_df["display_label"], plot_df["value"], color="#E45756")
    plt.axhline(0.0, color="black", linewidth=0.8)
    plt.xticks(rotation=75, ha="right", fontsize=8)
    plt.ylabel("Delta contacts vs WT")
    plt.xlabel("Variant")
    plt.title("Contact change relative to WT")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_mean_min_distance_by_position(peptide_position_df: pd.DataFrame, output_path: Path) -> None:
    grouped = peptide_position_df.groupby("peptide_position", dropna=True)["min_distance_to_mhc"].mean().reset_index()
    plt.figure(figsize=(6, 4))
    plt.bar(grouped["peptide_position"].astype(str), grouped["min_distance_to_mhc"], color="#72B7B2")
    plt.ylabel("Mean min distance to MHC")
    plt.xlabel("Peptide position")
    plt.title("Mean minimum distance by peptide position")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_position_disruption(position_df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(6, 4))
    values = pd.to_numeric(position_df["avg_delta_total_contacts_vs_wt"], errors="coerce").fillna(0.0)
    plt.bar(position_df["mutated_position"].astype(str), values, color="#B279A2")
    plt.axhline(0.0, color="black", linewidth=0.8)
    plt.ylabel("Avg delta contacts vs WT")
    plt.xlabel("Mutated position")
    plt.title("Position disruption summary")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_fingerprint_feature_values(
    fingerprint_df: pd.DataFrame,
    feature_cols: list[str],
    output_path: Path,
) -> None:
    plot_df = fingerprint_df[["variant_id", *feature_cols]].dropna(how="all", subset=feature_cols)
    if plot_df.empty:
        return
    matrix = plot_df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy()
    plt.figure(figsize=(max(8, 0.9 * len(feature_cols)), max(5, 0.5 * len(plot_df))))
    plt.imshow(matrix, aspect="auto", cmap="coolwarm")
    plt.colorbar(label="Feature value")
    plt.xticks(range(len(feature_cols)), feature_cols, rotation=45, ha="right")
    plt.yticks(range(len(plot_df)), plot_df["variant_id"])
    plt.title("Tolerance fingerprint feature values")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_coverage_overview(summary_df: pd.DataFrame, output_path: Path) -> None:
    categories = ["variants", "structures", "structural_metrics"]
    structures = int(summary_df["structure_path"].notna().sum()) if "structure_path" in summary_df.columns else 0
    structural_metrics = (
        int(summary_df["total_peptide_mhc_contacts"].notna().sum())
        if "total_peptide_mhc_contacts" in summary_df.columns
        else 0
    )
    values = [len(summary_df), structures, structural_metrics]
    plt.figure(figsize=(5, 4))
    plt.bar(categories, values, color=["#4C78A8", "#72B7B2", "#54A24B"])
    plt.ylabel("Count")
    plt.title("Project coverage overview")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _variant_labels(plot_df: pd.DataFrame) -> list[str]:
    if {"allele_name", "local_variant_id"}.issubset(plot_df.columns):
        return [
            f"{str(allele).replace('HLA-', '')}:{local}"
            for allele, local in zip(plot_df["allele_name"], plot_df["local_variant_id"])
        ]
    return plot_df["variant_id"].astype(str).tolist()
