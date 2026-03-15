import json

import pandas as pd

from src.config import ReportingConfig
from src.reporting import (
    build_analysis_snapshot,
    build_figure_manifest,
    build_markdown_report,
    build_report_summary,
    build_table_manifest,
    write_report_package,
)


def test_report_generation_with_partial_data(tmp_path) -> None:
    manifest_df = pd.DataFrame(
        [
            {"variant_id": "v1", "allele_name": "A", "peptide_id": "pep1"},
            {"variant_id": "v2", "allele_name": "B", "peptide_id": "pep1"},
        ]
    )
    summary_df = pd.DataFrame([{"variant_id": "v1", "structure_path": None, "total_peptide_mhc_contacts": None}])
    allele_df = pd.DataFrame([{"allele_name": "A", "mean_abs_delta_total_contacts_vs_wt": 1.2}])
    cross_df = pd.DataFrame([{"num_alleles": 2, "mean_abs_contact_change": 1.2}])
    hypotheses_df = pd.DataFrame([{"hypothesis_id": "h1", "statement": "Example", "caveats": "Exploratory only."}])

    plot_dir = tmp_path / "plots"
    analysis_dir = tmp_path / "analysis"
    plot_dir.mkdir()
    analysis_dir.mkdir()
    (plot_dir / "allele_similarity_heatmap.png").write_bytes(b"png")
    (analysis_dir / "table_project_coverage.csv").write_text("allele_name,num_variants\nA,1\n", encoding="utf-8")

    report_summary = build_report_summary(
        "demo",
        manifest_df,
        summary_df,
        allele_df,
        cross_df,
        hypotheses_df,
        [],
    )
    figure_manifest = build_figure_manifest(plot_dir, 4)
    table_manifest = build_table_manifest(analysis_dir, 4)
    snapshot = build_analysis_snapshot(
        "demo",
        manifest_df,
        summary_df,
        figure_manifest,
        table_manifest,
        {"timestamp_utc": "2026-01-01T00:00:00Z"},
        [],
        hypotheses_df,
    )
    markdown = build_markdown_report(report_summary, [], cross_df, hypotheses_df, ["Caveat."])
    report_path, summary_path = write_report_package(
        analysis_dir,
        ReportingConfig(True, True, True, True, True, 4, 4),
        report_summary,
        markdown,
        figure_manifest,
        table_manifest,
        snapshot,
    )

    assert report_path is not None and report_path.exists()
    assert summary_path is not None and summary_path.exists()
    assert (analysis_dir / "analysis_snapshot.json").exists()
    loaded = json.loads((analysis_dir / "report_summary.json").read_text(encoding="utf-8"))
    assert loaded["project_name"] == "demo"

