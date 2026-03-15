from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from .config import PublicationBundleConfig


def write_publication_bundle(
    bundle_dir: Path,
    config: PublicationBundleConfig,
    report_path: Path | None,
    report_summary_path: Path | None,
    figure_rows: list[dict[str, object]],
    table_rows: list[dict[str, object]],
    notebook_exports: dict[str, pd.DataFrame | dict[str, object]],
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = bundle_dir / "figures"
    tables_dir = bundle_dir / "tables"
    manifests_dir = bundle_dir / "manifests"
    notebook_dir = bundle_dir / "notebook_exports"
    for path in [figures_dir, tables_dir, manifests_dir, notebook_dir]:
        path.mkdir(parents=True, exist_ok=True)

    if report_path and report_path.exists():
        shutil.copy2(report_path, bundle_dir / "report.md")
    if report_summary_path and report_summary_path.exists():
        shutil.copy2(report_summary_path, bundle_dir / "report_summary.json")

    bundled_figures = _bundle_paths(figure_rows, figures_dir, config.copy_figures, "figure")
    bundled_tables = _bundle_paths(table_rows, tables_dir, config.copy_tables, "table")
    pd.DataFrame(bundled_figures).to_csv(manifests_dir / "figures_manifest.csv", index=False)
    pd.DataFrame(bundled_tables).to_csv(manifests_dir / "tables_manifest.csv", index=False)

    if config.include_notebook_exports:
        for name, payload in notebook_exports.items():
            output_path = notebook_dir / name
            if isinstance(payload, pd.DataFrame):
                payload.to_csv(output_path, index=False)
            else:
                output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _bundle_paths(
    rows: list[dict[str, object]],
    target_dir: Path,
    should_copy: bool,
    prefix: str,
) -> list[dict[str, object]]:
    bundled_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        source = Path(str(row.get("source_path", ""))) if row.get("source_path") else None
        bundled_path = ""
        if source and source.exists() and should_copy:
            normalized_name = f"{prefix}_{index:02d}{source.suffix.lower()}"
            destination = target_dir / normalized_name
            shutil.copy2(source, destination)
            bundled_path = str(destination)
        elif source and source.exists():
            bundled_path = str(source)
        bundled_rows.append({**row, "bundled_path": bundled_path})
    return bundled_rows
