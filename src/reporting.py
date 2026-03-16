from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import pandas as pd

from .config import ReportingConfig
from .scope_text import brief_scope_markdown, expanded_scope_markdown


def build_report_summary(
    config_name: str,
    manifest_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    allele_tolerance_df: pd.DataFrame,
    cross_allele_summary_df: pd.DataFrame,
    hypotheses_df: pd.DataFrame,
    case_study_results: list[dict[str, object]],
    priority_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    prediction_count = int(summary_df["structure_path"].notna().sum()) if "structure_path" in summary_df.columns else 0
    structural_count = (
        int(summary_df["total_peptide_mhc_contacts"].notna().sum())
        if "total_peptide_mhc_contacts" in summary_df.columns
        else 0
    )
    return {
        "project_name": config_name,
        "num_alleles": int(manifest_df["allele_name"].nunique()) if "allele_name" in manifest_df.columns else 0,
        "num_variants": int(len(manifest_df)),
        "num_predictions_with_structures": prediction_count,
        "num_variants_with_structural_metrics": structural_count,
        "alleles": sorted(manifest_df["allele_name"].dropna().unique().tolist()) if "allele_name" in manifest_df.columns else [],
        "mean_abs_contact_change": _safe_float(
            allele_tolerance_df.get("mean_abs_delta_total_contacts_vs_wt", pd.Series(dtype=float)).mean()
        ),
        "cross_allele_summary_rows": int(len(cross_allele_summary_df)),
        "hypothesis_count": int(len(hypotheses_df)),
        "case_study_count": int(len(case_study_results)),
        "priority_row_count": int(len(priority_df)) if priority_df is not None else 0,
        "panel_row_count": int(len(panel_df)) if panel_df is not None else 0,
    }


def build_markdown_report(
    report_summary: dict[str, object],
    case_study_results: list[dict[str, object]],
    cross_allele_summary_df: pd.DataFrame,
    hypotheses_df: pd.DataFrame,
    caveats: list[str],
    priority_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
) -> str:
    lines = [
        "# Peptide-MHC Comparative Structural Report",
        "",
        "## Study Overview",
        "",
        f"- Project: {report_summary['project_name']}",
        f"- Alleles analyzed: {report_summary['num_alleles']}",
        f"- Variants analyzed: {report_summary['num_variants']}",
        f"- Structures available: {report_summary['num_predictions_with_structures']}",
        f"- Variants with structural metrics: {report_summary['num_variants_with_structural_metrics']}",
        "",
        "## Cross-Allele Summary",
        "",
    ]
    if cross_allele_summary_df.empty:
        lines.append("Cross-allele summary outputs were not available for this run.")
    else:
        for row in cross_allele_summary_df.to_dict(orient="records"):
            lines.append(
                f"- Across {row.get('num_alleles', 'NA')} allele(s), mean absolute contact change was {row.get('mean_abs_contact_change', 'NA')}."
            )
    lines.extend(["", "## Case Studies", ""])
    if not case_study_results:
        lines.append("No case studies were configured or no matching data were available.")
    else:
        for case in case_study_results:
            lines.append(
                f"- `{case['case_id']}`: {case['description']} ({case['num_variants']} filtered variants, status={case['status']})."
            )
    lines.extend(["", "## Prioritized Findings", ""])
    if priority_df is None or priority_df.empty:
        lines.append("No prioritization rows were available for this run.")
    else:
        for mode_name in ["disruptive_mutations", "tolerated_mutations", "allele_discriminating_mutations"]:
            subset = priority_df[priority_df["ranking_mode"] == mode_name].head(3)
            if subset.empty:
                continue
            lines.append(f"### {mode_name}")
            for row in subset.to_dict(orient="records"):
                lines.append(
                    f"- `{row['variant_id']}` rank {row['priority_rank']} score {row['priority_score']}. "
                    f"Coverage {row.get('evidence_coverage_score', 'NA')}, uncertainty {row.get('uncertainty_flag', 'NA')}."
                )
    lines.extend(["", "## Panel Design", ""])
    if panel_df is None or panel_df.empty:
        lines.append("No compact mutation panels were selected for this run.")
    else:
        for row in panel_df.head(5).to_dict(orient="records"):
            lines.append(
                f"- `{row['panel_id']}` includes `{row['variant_id']}` ({row['selection_reason']})."
            )
    lines.extend(["", "## Exploratory Hypotheses", ""])
    if hypotheses_df.empty:
        lines.append("No exploratory hypotheses met the configured support thresholds.")
    else:
        for row in hypotheses_df.to_dict(orient="records"):
            lines.append(f"- {row['statement']} Caveat: {row['caveats']}")
    lines.extend(["", "## Caveats", ""])
    for caveat in caveats:
        lines.append(f"- {caveat}")
    lines.extend(["", brief_scope_markdown(), "", expanded_scope_markdown()])
    return "\n".join(lines)


def build_printable_report(
    report_summary: dict[str, object],
    priority_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
) -> str:
    """Build a simplified, high-contrast report for printing/PDF."""
    lines = [
        f"# Executive Summary: {report_summary['project_name']}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Key Metrics",
        f"- **Alleles**: {report_summary['num_alleles']}",
        f"- **Variants**: {report_summary['num_variants']}",
        f"- **Structural Coverage**: {report_summary['num_variants_with_structural_metrics']} variants",
        "",
        "## Top Prioritized Variants",
    ]
    if priority_df is not None and not priority_df.empty:
        top_v = priority_df.head(10)
        for _, row in top_v.iterrows():
            lines.append(f"- **{row['variant_id']}** (Rank {row['priority_rank']}): Score {row['priority_score']:.2f}")
    else:
        lines.append("No prioritized data available.")

    lines.extend([
        "",
        "## Scientific Guardrails",
        expanded_scope_markdown()
    ])
    return "\n".join(lines)


def build_figure_manifest(
    plot_dir: Path,
    core_figure_limit: int,
) -> pd.DataFrame:
    figure_specs = [
        ("fig_coverage", plot_dir / "coverage_overview.png", "Coverage overview", "Prediction and structural coverage by variant.", "study_overview"),
        ("fig_delta_contacts", plot_dir / "delta_contacts_vs_wt_by_mutant.png", "WT-relative contact disruption", "Per-variant total contact change relative to WT.", "within_allele_analysis"),
        ("fig_similarity", plot_dir / "allele_similarity_heatmap.png", "Allele similarity heatmap", "Cross-allele combined similarity over tolerance and pocket features.", "cross_allele_analysis"),
        ("fig_pocket_overlap", plot_dir / "pocket_overlap_heatmap.png", "Pocket overlap heatmap", "Jaccard overlap of raw contacting-residue sets across alleles.", "pocket_signature_analysis"),
        ("fig_position_sensitivity", plot_dir / "position_sensitivity_by_allele.png", "Allele position sensitivity", "Mean position-level disruption by allele.", "cross_allele_analysis"),
        ("fig_top_disruptive", plot_dir / "top_disruptive_variants.png", "Top disruptive variants", "Priority scores for disruptive mutation follow-up.", "within_allele_analysis"),
        ("fig_priority_vs_coverage", plot_dir / "priority_score_vs_coverage.png", "Priority score vs evidence coverage", "Decision-support view of score against support completeness.", "study_overview"),
        ("fig_panel_composition", plot_dir / "panel_composition.png", "Panel composition", "Selected panel composition across alleles, positions, and substitutions.", "study_overview"),
    ]
    rows = [_manifest_row(figure_id, path, title, description, section) for figure_id, path, title, description, section in figure_specs]
    return pd.DataFrame(rows[:core_figure_limit])


def build_table_manifest(
    analysis_dir: Path,
    core_table_limit: int,
) -> pd.DataFrame:
    table_specs = [
        ("table_project_coverage", analysis_dir / "table_project_coverage.csv", "Project coverage", "Per-allele coverage and structural completeness summary.", "study_overview"),
        ("table_top_disruptive_variants", analysis_dir / "table_top_disruptive_variants.csv", "Top disruptive variants", "Largest WT-relative structural disruption rows by allele.", "within_allele_analysis"),
        ("table_shared_contact_features", analysis_dir / "table_shared_contact_features.csv", "Shared contact features", "Shared contacting residues or regions across alleles.", "cross_allele_analysis"),
        ("table_allele_distinguishing_features", analysis_dir / "table_allele_distinguishing_features.csv", "Allele-distinguishing features", "Allele-specific contact or tolerance features.", "cross_allele_analysis"),
        ("table_hypothesis_summary", analysis_dir / "table_hypothesis_summary.csv", "Hypothesis summary", "Exploratory hypotheses and their supporting evidence.", "hypothesis_generation"),
        ("table_priority_summary", analysis_dir / "table_priority_summary.csv", "Priority summary", "Top-ranked variants for each prioritization mode.", "within_allele_analysis"),
        ("table_panel_summary", analysis_dir / "table_panel_summary.csv", "Panel summary", "Compact panel selections and coverage summaries.", "study_overview"),
    ]
    rows = [_manifest_row(table_id, path, title, description, section) for table_id, path, title, description, section in table_specs]
    return pd.DataFrame(rows[:core_table_limit])


def write_report_package(
    analysis_dir: Path,
    config: ReportingConfig,
    report_summary: dict[str, object],
    report_markdown: str,
    figure_manifest_df: pd.DataFrame,
    table_manifest_df: pd.DataFrame,
    analysis_snapshot: dict[str, object],
) -> tuple[Path | None, Path | None]:
    if not config.enabled:
        return None, None
    report_path = analysis_dir / "report.md"
    summary_path = analysis_dir / "report_summary.json"
    if config.generate_markdown_report:
        report_path.write_text(report_markdown, encoding="utf-8")
    summary_path.write_text(json.dumps(report_summary, indent=2), encoding="utf-8")
    figure_manifest_df.to_csv(analysis_dir / "figures_manifest.csv", index=False)
    table_manifest_df.to_csv(analysis_dir / "tables_manifest.csv", index=False)
    (analysis_dir / "analysis_snapshot.json").write_text(json.dumps(analysis_snapshot, indent=2), encoding="utf-8")
    return report_path if config.generate_markdown_report else None, summary_path


def build_analysis_snapshot(
    project_name: str,
    manifest_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    figure_manifest_df: pd.DataFrame,
    table_manifest_df: pd.DataFrame,
    provenance: dict[str, str],
    case_study_results: list[dict[str, object]],
    hypotheses_df: pd.DataFrame,
    priority_df: pd.DataFrame | None = None,
    panel_df: pd.DataFrame | None = None,
    robustness_summary_df: pd.DataFrame | None = None,
    benchmark_summary_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    return {
        "project_name": project_name,
        "timestamp_utc": provenance.get("timestamp_utc"),
        "provenance": provenance,
        "num_alleles": int(manifest_df["allele_name"].nunique()) if "allele_name" in manifest_df.columns else 0,
        "num_peptides": int(manifest_df["peptide_id"].nunique()) if "peptide_id" in manifest_df.columns else 0,
        "num_variants": int(len(manifest_df)),
        "prediction_coverage": int(summary_df["structure_path"].notna().sum()) if "structure_path" in summary_df.columns else 0,
        "structural_coverage": int(summary_df["total_peptide_mhc_contacts"].notna().sum()) if "total_peptide_mhc_contacts" in summary_df.columns else 0,
        "generated_figures": figure_manifest_df.to_dict(orient="records"),
        "generated_tables": table_manifest_df.to_dict(orient="records"),
        "case_studies": case_study_results,
        "hypothesis_count": int(len(hypotheses_df)),
        "priority_row_count": int(len(priority_df)) if priority_df is not None else 0,
        "panel_row_count": int(len(panel_df)) if panel_df is not None else 0,
        "robustness_runs": int(len(robustness_summary_df)) if robustness_summary_df is not None else 0,
        "benchmark_rows": int(len(benchmark_summary_df)) if benchmark_summary_df is not None else 0,
    }


def build_publication_tables(
    summary_df: pd.DataFrame,
    allele_tolerance_df: pd.DataFrame,
    pocket_signature_residues_df: pd.DataFrame,
    hypotheses_df: pd.DataFrame,
    analysis_dir: Path,
    priority_df: pd.DataFrame | None = None,
    panel_coverage_df: pd.DataFrame | None = None,
) -> dict[str, Path]:
    outputs: dict[str, Path] = {}

    if not summary_df.empty and "allele_name" in summary_df.columns:
        coverage_df = (
            summary_df.groupby("allele_name", dropna=True)
            .agg(
                num_variants=("variant_id", "nunique"),
                num_structures=("structure_path", lambda values: int(pd.Series(values).notna().sum())),
                num_structural_metric_rows=(
                    "total_peptide_mhc_contacts",
                    lambda values: int(pd.Series(values).notna().sum()),
                ),
            )
            .reset_index()
        )
    else:
        coverage_df = pd.DataFrame()
    outputs["table_project_coverage.csv"] = analysis_dir / "table_project_coverage.csv"
    coverage_df.to_csv(outputs["table_project_coverage.csv"], index=False)

    disruptive_df = pd.DataFrame()
    if "delta_total_contacts_vs_wt" in summary_df.columns and not summary_df.empty:
        disruptive_df = summary_df.sort_values("delta_total_contacts_vs_wt").head(10).copy()
    outputs["table_top_disruptive_variants.csv"] = analysis_dir / "table_top_disruptive_variants.csv"
    disruptive_df.to_csv(outputs["table_top_disruptive_variants.csv"], index=False)

    shared_df = (
        pocket_signature_residues_df.groupby("mhc_residue_identifier", dropna=True)
        .agg(
            allele_count=("allele_name", "nunique"),
            alleles=("allele_name", lambda values: ";".join(sorted(set(values)))),
        )
        .reset_index()
        if not pocket_signature_residues_df.empty
        else pd.DataFrame()
    )
    outputs["table_shared_contact_features.csv"] = analysis_dir / "table_shared_contact_features.csv"
    shared_df.to_csv(outputs["table_shared_contact_features.csv"], index=False)

    distinguishing_df = allele_tolerance_df.copy()
    outputs["table_allele_distinguishing_features.csv"] = analysis_dir / "table_allele_distinguishing_features.csv"
    distinguishing_df.to_csv(outputs["table_allele_distinguishing_features.csv"], index=False)

    outputs["table_hypothesis_summary.csv"] = analysis_dir / "table_hypothesis_summary.csv"
    hypotheses_df.to_csv(outputs["table_hypothesis_summary.csv"], index=False)
    outputs["table_priority_summary.csv"] = analysis_dir / "table_priority_summary.csv"
    (priority_df if priority_df is not None else pd.DataFrame()).to_csv(outputs["table_priority_summary.csv"], index=False)
    outputs["table_panel_summary.csv"] = analysis_dir / "table_panel_summary.csv"
    (panel_coverage_df if panel_coverage_df is not None else pd.DataFrame()).to_csv(outputs["table_panel_summary.csv"], index=False)
    return outputs


def _manifest_row(
    entry_id: str,
    source_path: Path,
    title: str,
    description: str,
    section: str,
) -> dict[str, object]:
    return {
        "figure_id" if entry_id.startswith("fig_") else "table_id": entry_id,
        "source_path": str(source_path),
        "bundled_path": "",
        "title": title,
        "description": description,
        "section": section,
        "status": "ok" if source_path.exists() else "missing",
        "notes": "Selected from the current run's publication-oriented core set.",
    }


def _safe_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
