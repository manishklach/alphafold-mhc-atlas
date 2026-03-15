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
    priority_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
    ranking_stability_df: pd.DataFrame | None = None,
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

    if priority_df is not None and not priority_df.empty:
        disruptive_plot = plot_dir / "top_disruptive_variants.png"
        _plot_top_priority(priority_df, "disruptive_mutations", disruptive_plot, "Top disruptive variants")
        if disruptive_plot.exists():
            plot_paths.append(disruptive_plot)

        tolerated_plot = plot_dir / "top_tolerated_variants.png"
        _plot_top_priority(priority_df, "tolerated_mutations", tolerated_plot, "Top tolerated variants")
        if tolerated_plot.exists():
            plot_paths.append(tolerated_plot)

        score_cov = plot_dir / "priority_score_vs_coverage.png"
        _plot_priority_vs_coverage(priority_df, score_cov)
        if score_cov.exists():
            plot_paths.append(score_cov)

        discrimination_plot = plot_dir / "allele_discrimination_scores.png"
        _plot_top_priority(priority_df, "allele_discriminating_mutations", discrimination_plot, "Allele discrimination scores")
        if discrimination_plot.exists():
            plot_paths.append(discrimination_plot)

    if ranking_stability_df is not None and not ranking_stability_df.empty:
        stability_plot = plot_dir / "ranking_stability.png"
        _plot_ranking_stability(ranking_stability_df, stability_plot)
        if stability_plot.exists():
            plot_paths.append(stability_plot)

    if panel_df is not None and not panel_df.empty:
        panel_plot = plot_dir / "panel_composition.png"
        _plot_panel_composition(panel_df, panel_plot)
        if panel_plot.exists():
            plot_paths.append(panel_plot)

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


def _plot_top_priority(priority_df: pd.DataFrame, mode_name: str, output_path: Path, title: str) -> None:
    subset = priority_df[priority_df["ranking_mode"] == mode_name].head(10).copy()
    if subset.empty:
        return
    plt.figure(figsize=(8, 4.5))
    labels = subset["variant_id"].astype(str)
    values = pd.to_numeric(subset["priority_score"], errors="coerce").fillna(0.0)
    plt.bar(labels, values, color="#0F6D66")
    plt.xticks(rotation=70, ha="right", fontsize=8)
    plt.ylabel("Priority score")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_priority_vs_coverage(priority_df: pd.DataFrame, output_path: Path) -> None:
    working = priority_df.copy()
    if working.empty:
        return
    x = pd.to_numeric(working["evidence_coverage_score"], errors="coerce").fillna(0.0)
    y = pd.to_numeric(working["priority_score"], errors="coerce").fillna(0.0)
    plt.figure(figsize=(6, 5))
    plt.scatter(x, y, color="#B35F3F", alpha=0.8)
    plt.xlabel("Evidence coverage score")
    plt.ylabel("Priority score")
    plt.title("Priority score vs evidence coverage")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_ranking_stability(ranking_stability_df: pd.DataFrame, output_path: Path) -> None:
    working = ranking_stability_df.copy()
    if working.empty:
        return
    grouped = working.groupby("ranking_mode", dropna=False)["rank_shift"].apply(
        lambda values: pd.to_numeric(values, errors="coerce").abs().mean()
    ).reset_index(name="mean_abs_rank_shift")
    plt.figure(figsize=(7, 4))
    plt.bar(grouped["ranking_mode"], grouped["mean_abs_rank_shift"], color="#B279A2")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Mean absolute rank shift")
    plt.title("Ranking stability")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _plot_panel_composition(panel_df: pd.DataFrame, output_path: Path) -> None:
    working = panel_df.copy()
    if working.empty:
        return
    grouped = working.groupby("allele_name", dropna=False)["variant_id"].nunique().reset_index(name="count")
    plt.figure(figsize=(6, 4))
    plt.bar(grouped["allele_name"], grouped["count"], color="#4C78A8")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Selected variants")
    plt.title("Panel composition by allele")
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
