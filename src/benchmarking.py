from __future__ import annotations

import pandas as pd

from .config import BenchmarkingConfig


def run_benchmarking(
    summary_df: pd.DataFrame,
    fingerprint_df: pd.DataFrame,
    benchmark_config: BenchmarkingConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []
    reference_rows: list[dict[str, object]] = []
    warning_rows: list[dict[str, object]] = []

    if not benchmark_config.enabled:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    summary_rows.append(
        {
            "benchmark_mode": "internal_consistency_benchmark",
            "status": "ok",
            "metric_name": "variants_with_summary_rows",
            "metric_value": int(len(summary_df)),
            "notes": "Checks whether summary rows were produced for the current project.",
        }
    )
    summary_rows.append(
        {
            "benchmark_mode": "wt_vs_mutant_completeness_benchmark",
            "status": "ok",
            "metric_name": "wildtype_rows_present",
            "metric_value": int(summary_df.get("is_wildtype", pd.Series(dtype=bool)).fillna(False).sum()),
            "notes": "Counts WT rows available for comparison.",
        }
    )
    summary_rows.append(
        {
            "benchmark_mode": "threshold_consistency_benchmark",
            "status": "not_benchmarked",
            "metric_name": "contact_thresholds_recomputed",
            "metric_value": 0,
            "notes": "Threshold consistency requires alternate contact recomputation, which is not available in the current run.",
        }
    )

    structural_coverage = (
        int(summary_df["total_peptide_mhc_contacts"].notna().sum())
        if "total_peptide_mhc_contacts" in summary_df.columns
        else 0
    )
    if structural_coverage == 0:
        warning_rows.append(
            {
                "warning_type": "no_structural_coverage",
                "severity": "warning",
                "notes": "No structural coverage was available, so structural prioritization evidence is limited.",
            }
        )
    if benchmark_config.reference_structure_map:
        reference_rows.append(
            {
                "benchmark_mode": "reference_structure_comparison",
                "status": "not_benchmarked",
                "notes": "Reference structure comparison hook is configured but not implemented beyond file tracking in phase 6.",
                "reference_input": str(benchmark_config.reference_structure_map),
            }
        )
    else:
        reference_rows.append(
            {
                "benchmark_mode": "reference_structure_comparison",
                "status": "skipped",
                "notes": "No reference structure mapping file was supplied.",
                "reference_input": "",
            }
        )

    if not fingerprint_df.empty:
        detail_rows.extend(
            [
                {
                    "benchmark_mode": "internal_consistency_benchmark",
                    "detail_name": "fingerprint_rows",
                    "detail_value": int(len(fingerprint_df)),
                    "notes": "Counts variant-level fingerprint rows.",
                },
                {
                    "benchmark_mode": "wt_vs_mutant_completeness_benchmark",
                    "detail_name": "mutant_rows",
                    "detail_value": int(
                        fingerprint_df.get("mutated_position", pd.Series(dtype=float)).notna().sum()
                    ),
                    "notes": "Counts mutant rows that entered fingerprinting.",
                },
            ]
        )

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(detail_rows),
        pd.DataFrame(reference_rows),
        pd.DataFrame(warning_rows),
    )
