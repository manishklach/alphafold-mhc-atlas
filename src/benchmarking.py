from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config
from .benchmark_schema import get_benchmark_template, BenchmarkTemplate


def run_benchmark_comparison(
    workspace: WorkspaceConfig | str | Path,
    benchmark_id: str,
    benchmark_data_path: Path
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    template = get_benchmark_template(benchmark_id)
    
    output_dir = config.output_dir / "benchmarks" / benchmark_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load External Data
    ext_df = safe_read_csv(benchmark_data_path)
    if ext_df.empty:
        raise ValueError(f"Benchmark data at {benchmark_data_path} is empty.")

    # 2. Load Internal Structural Evidence (Summary Table)
    # We aggregate from all projects in workspace
    internal_dfs = []
    for project in config.projects:
        summary_path = project.path / "analysis" / "summary_table.csv"
        if summary_path.exists():
            df = safe_read_csv(summary_path)
            df["project_id"] = project.project_id
            internal_dfs.append(df)
            
    if not internal_dfs:
        internal_df = pd.DataFrame(columns=["variant_id", "allele_name", "total_contacts", "contact_delta_wt"])
    else:
        internal_df = pd.concat(internal_dfs, ignore_index=True)

    # 3. Join on ID and Allele
    id_col = template.columns.get("id_col", "variant_id")
    allele_col = template.columns.get("allele_col", "allele_name")
    
    # Map internal columns if necessary (variant_id vs peptide_id)
    # For now assume internal always has variant_id and allele_name
    merged = internal_df.merge(
        ext_df,
        left_on=["variant_id", "allele_name"],
        right_on=[id_col, allele_col],
        how="inner"
    )

    # 4. Compute Alignment Metrics
    # Example: Correlation between structural contacts and benchmark affinity
    alignment_summary = {
        "benchmark_id": benchmark_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_intersecting_variants": len(merged),
        "projects_covered": merged["project_id"].unique().tolist() if "project_id" in merged.columns else []
    }

    # 5. Write Outputs
    comparison_path = output_dir / "benchmark_comparison.csv"
    merged.to_csv(comparison_path, index=False)
    
    summary_path = output_dir / "benchmark_summary.json"
    summary_path.write_text(json.dumps(alignment_summary, indent=2), encoding="utf-8")
    
    md_path = output_dir / "benchmark_report.md"
    lines = [
        f"# Benchmark Report: {template.label}",
        f"**Source**: {template.data_source}",
        f"**Intersecting Variants**: {len(merged)}",
        "",
        "## Alignment Overview",
        "This report compares exploratory structural evidence against external benchmark data.",
        "",
        "### Top Intersecting Variants",
    ]
    if not merged.empty:
        for _, row in merged.head(10).iterrows():
            lines.append(f"- **{row['variant_id']}** ({row['allele_name']}): Structural Contacts: {row.get('total_contacts', 'N/A')} | Benchmark Outcome: {row.get(template.columns.get('outcome_col'), 'N/A')}")
    else:
        lines.append("- No intersection found between workspace and benchmark data.")
        
    lines.extend([
        "",
        "## Caveats",
        "Benchmark alignment is descriptive. Overlap does not prove predictive accuracy, as structural models remain exploratory hypotheses."
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "benchmark_comparison.csv": comparison_path,
        "benchmark_summary.json": summary_path,
        "benchmark_report.md": md_path
    }
