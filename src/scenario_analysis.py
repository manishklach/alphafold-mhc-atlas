from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .evidence_view import build_variant_evidence_bundle
from .filtering import apply_variant_filters
from .scenario_state import ScenarioState


def run_scenario_analysis(
    scenario: ScenarioState,
    tables: dict[str, pd.DataFrame],
    output_dir: Path | None = None,
) -> dict[str, object]:
    priority_df = tables.get("priority", pd.DataFrame())
    panel_df = tables.get("panel", pd.DataFrame())
    evidence_df = tables.get("priority_evidence", pd.DataFrame())

    filtered_priority = apply_variant_filters(
        priority_df,
        alleles=scenario.alleles,
        peptides=scenario.peptides,
        positions=scenario.mutation_positions,
        substitutions=scenario.substitutions,
        ranking_mode=scenario.ranking_mode,
        evidence_coverage_min=scenario.evidence_coverage_threshold,
        allowed_uncertainty=scenario.allowed_uncertainty,
        require_structural_support=scenario.require_structural_support,
    )
    if scenario.anchor_only and "mutated_position" in filtered_priority.columns:
        anchor_positions = set(scenario.mutation_positions)
        if anchor_positions:
            filtered_priority = filtered_priority[
                pd.to_numeric(filtered_priority["mutated_position"], errors="coerce").isin(anchor_positions)
            ].reset_index(drop=True)

    filtered_panel = apply_variant_filters(
        panel_df,
        alleles=scenario.alleles,
        peptides=scenario.peptides,
        positions=scenario.mutation_positions,
        substitutions=scenario.substitutions,
    )
    if scenario.panel_size is not None and not filtered_panel.empty:
        filtered_panel = filtered_panel.head(scenario.panel_size).reset_index(drop=True)

    variant_ids = filtered_priority["variant_id"].tolist() if "variant_id" in filtered_priority.columns else []
    filtered_evidence = (
        evidence_df[evidence_df["variant_id"].isin(variant_ids)].reset_index(drop=True)
        if not evidence_df.empty and "variant_id" in evidence_df.columns
        else pd.DataFrame()
    )
    summary = _build_scenario_summary(scenario, filtered_priority, filtered_panel)
    notes = _build_scenario_notes(summary)

    result = {
        "scenario": scenario.to_dict(),
        "summary": summary,
        "ranked_variants": filtered_priority,
        "panel": filtered_panel,
        "evidence": filtered_evidence,
        "notes_markdown": notes,
    }
    if output_dir is not None:
        export_scenario_result(result, output_dir)
    return result


def compare_scenarios(
    scenario_a: dict[str, object],
    scenario_b: dict[str, object],
    output_dir: Path | None = None,
) -> dict[str, object]:
    ranks_a = scenario_a["ranked_variants"].copy()
    ranks_b = scenario_b["ranked_variants"].copy()
    panel_a = scenario_a["panel"].copy()
    panel_b = scenario_b["panel"].copy()

    rank_diff = _rank_diff(ranks_a, ranks_b)
    panel_diff = _panel_diff(panel_a, panel_b)
    comparison = pd.DataFrame(
        [
            {
                "scenario_a": scenario_a["scenario"]["scenario_id"],
                "scenario_b": scenario_b["scenario"]["scenario_id"],
                "rank_overlap": int(len(set(ranks_a.get("variant_id", [])) & set(ranks_b.get("variant_id", [])))),
                "panel_overlap": int(len(set(panel_a.get("variant_id", [])) & set(panel_b.get("variant_id", [])))),
                "mean_evidence_a": _safe_mean(ranks_a, "evidence_coverage_score"),
                "mean_evidence_b": _safe_mean(ranks_b, "evidence_coverage_score"),
            }
        ]
    )
    markdown = _comparison_markdown(comparison, panel_diff, rank_diff)
    result = {
        "comparison": comparison,
        "rank_diff": rank_diff,
        "panel_diff": panel_diff,
        "summary_markdown": markdown,
    }
    if output_dir is not None:
        export_scenario_comparison(result, output_dir)
    return result


def export_scenario_result(result: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario = result["scenario"]
    summary_df = pd.DataFrame([result["summary"]])
    summary_df.to_csv(output_dir / "scenario_summary.csv", index=False)
    (output_dir / "scenario_summary.json").write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")
    result["ranked_variants"].to_csv(output_dir / "scenario_ranked_variants.csv", index=False)
    result["panel"].to_csv(output_dir / "scenario_panel.csv", index=False)
    result["evidence"].to_csv(output_dir / "scenario_evidence.csv", index=False)
    (output_dir / "scenario_notes.md").write_text(result["notes_markdown"], encoding="utf-8")
    (output_dir / "saved_scenario.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")

    evidence_rows = []
    for variant_id in result["ranked_variants"].get("variant_id", []).tolist()[:10]:
        evidence_rows.append(
            {
                "variant_id": variant_id,
                "bundle_path": f"evidence_bundle_{variant_id}.json",
            }
        )
    pd.DataFrame(evidence_rows).to_csv(output_dir / "evidence_manifest.csv", index=False)
    return output_dir


def export_scenario_comparison(result: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    result["comparison"].to_csv(output_dir / "scenario_comparison.csv", index=False)
    result["rank_diff"].to_csv(output_dir / "scenario_rank_diff.csv", index=False)
    result["panel_diff"].to_csv(output_dir / "scenario_panel_diff.csv", index=False)
    (output_dir / "scenario_comparison_summary.md").write_text(result["summary_markdown"], encoding="utf-8")
    (output_dir / "comparison_summary.json").write_text(
        json.dumps(result["comparison"].to_dict(orient="records"), indent=2),
        encoding="utf-8",
    )
    return output_dir


def build_evidence_exports(result: dict[str, object], tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = result["ranked_variants"]
    if ranked.empty or "variant_id" not in ranked.columns:
        return
    for variant_id in ranked["variant_id"].head(10).tolist():
        bundle = build_variant_evidence_bundle(str(variant_id), tables)
        (output_dir / f"evidence_bundle_{variant_id}.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")


def _build_scenario_summary(
    scenario: ScenarioState,
    filtered_priority: pd.DataFrame,
    filtered_panel: pd.DataFrame,
) -> dict[str, object]:
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "ranking_mode": scenario.ranking_mode,
        "num_ranked_variants": int(len(filtered_priority)),
        "num_panel_rows": int(len(filtered_panel)),
        "num_alleles_covered": int(filtered_priority["allele_name"].nunique()) if "allele_name" in filtered_priority.columns else 0,
        "num_positions_covered": int(filtered_priority["mutated_position"].nunique()) if "mutated_position" in filtered_priority.columns else 0,
        "mean_evidence_coverage": _safe_mean(filtered_priority, "evidence_coverage_score"),
        "uncertainty_levels": sorted(set(filtered_priority.get("uncertainty_flag", pd.Series(dtype=object)).dropna().astype(str))),
    }


def _build_scenario_notes(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# Scenario: {summary['scenario_id']}",
            "",
            f"- Ranking mode: {summary['ranking_mode']}",
            f"- Ranked variants: {summary['num_ranked_variants']}",
            f"- Panel rows: {summary['num_panel_rows']}",
            f"- Mean evidence coverage: {summary['mean_evidence_coverage']}",
            "- Scenario outputs are filtered from existing analysis artifacts and do not rerun inference.",
        ]
    )


def _rank_diff(ranks_a: pd.DataFrame, ranks_b: pd.DataFrame) -> pd.DataFrame:
    if ranks_a.empty and ranks_b.empty:
        return pd.DataFrame()
    left = ranks_a[["variant_id", "priority_rank", "priority_score"]].rename(
        columns={"priority_rank": "rank_a", "priority_score": "score_a"}
    ) if {"variant_id", "priority_rank", "priority_score"}.issubset(ranks_a.columns) else pd.DataFrame(columns=["variant_id", "rank_a", "score_a"])
    right = ranks_b[["variant_id", "priority_rank", "priority_score"]].rename(
        columns={"priority_rank": "rank_b", "priority_score": "score_b"}
    ) if {"variant_id", "priority_rank", "priority_score"}.issubset(ranks_b.columns) else pd.DataFrame(columns=["variant_id", "rank_b", "score_b"])
    merged = left.merge(right, on="variant_id", how="outer")
    merged["rank_shift"] = pd.to_numeric(merged.get("rank_b"), errors="coerce") - pd.to_numeric(merged.get("rank_a"), errors="coerce")
    return merged.sort_values(["rank_a", "rank_b"], na_position="last").reset_index(drop=True)


def _panel_diff(panel_a: pd.DataFrame, panel_b: pd.DataFrame) -> pd.DataFrame:
    variants_a = set(panel_a["variant_id"].tolist()) if "variant_id" in panel_a.columns else set()
    variants_b = set(panel_b["variant_id"].tolist()) if "variant_id" in panel_b.columns else set()
    rows = []
    for variant_id in sorted(variants_a | variants_b):
        rows.append(
            {
                "variant_id": variant_id,
                "in_scenario_a": variant_id in variants_a,
                "in_scenario_b": variant_id in variants_b,
                "status": _panel_status(variant_id in variants_a, variant_id in variants_b),
            }
        )
    return pd.DataFrame(rows)


def _panel_status(in_a: bool, in_b: bool) -> str:
    if in_a and in_b:
        return "shared"
    if in_a:
        return "only_a"
    return "only_b"


def _comparison_markdown(comparison_df: pd.DataFrame, panel_diff: pd.DataFrame, rank_diff: pd.DataFrame) -> str:
    if comparison_df.empty:
        return "# Scenario Comparison\n\nNo scenario comparison rows were available."
    row = comparison_df.iloc[0].to_dict()
    changed = int(panel_diff[panel_diff["status"] != "shared"].shape[0]) if not panel_diff.empty else 0
    mean_shift = _safe_mean(rank_diff, "rank_shift")
    return "\n".join(
        [
            "# Scenario Comparison",
            "",
            f"- Scenario A: {row['scenario_a']}",
            f"- Scenario B: {row['scenario_b']}",
            f"- Rank overlap: {row['rank_overlap']}",
            f"- Panel overlap: {row['panel_overlap']}",
            f"- Changed panel members: {changed}",
            f"- Mean rank shift: {mean_shift}",
        ]
    )


def _safe_mean(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.mean())
