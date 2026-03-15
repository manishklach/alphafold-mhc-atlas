from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_variant_evidence_bundle(variant_id: str, tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    priority_df = tables.get("priority", pd.DataFrame())
    evidence_df = tables.get("priority_evidence", pd.DataFrame())
    uncertainty_df = tables.get("priority_uncertainty", pd.DataFrame())
    summary_df = tables.get("summary", pd.DataFrame())
    cross_allele_df = tables.get("cross_allele_summary", pd.DataFrame())
    panel_df = tables.get("panel", pd.DataFrame())

    priority_rows = _rows_for_variant(priority_df, variant_id)
    ranking_modes = sorted({row.get("ranking_mode", "") for row in priority_rows if row.get("ranking_mode")})
    return {
        "variant_id": variant_id,
        "priority_rows": priority_rows,
        "evidence_rows": _rows_for_variant(evidence_df, variant_id),
        "uncertainty_rows": _rows_for_variant(uncertainty_df, variant_id),
        "summary_rows": _rows_for_variant(summary_df, variant_id),
        "panel_rows": _rows_for_variant(panel_df, variant_id),
        "cross_allele_rows": _rows_for_variant(cross_allele_df, variant_id),
        "ranking_modes": ranking_modes,
        "notes": _bundle_notes(priority_rows),
    }


def export_variant_evidence_bundle(bundle: dict[str, object], output_path: Path) -> Path:
    output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return output_path


def _rows_for_variant(df: pd.DataFrame, variant_id: str) -> list[dict[str, object]]:
    if df.empty or "variant_id" not in df.columns:
        return []
    rows = df[df["variant_id"] == variant_id]
    return rows.to_dict(orient="records")


def _bundle_notes(priority_rows: list[dict[str, object]]) -> list[str]:
    if not priority_rows:
        return ["No prioritization rows were available for this variant."]
    return [
        "Evidence bundle is file-backed and reflects existing analysis outputs only.",
        "Priority scores remain drillable to component evidence rows.",
    ]
