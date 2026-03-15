from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import HypothesisGenerationConfig


@dataclass(frozen=True)
class HypothesisResult:
    hypotheses_df: pd.DataFrame
    markdown: str
    evidence: dict[str, object]


def build_hypotheses(
    fingerprint_df: pd.DataFrame,
    allele_tolerance_df: pd.DataFrame,
    cross_allele_summary_df: pd.DataFrame,
    pocket_signature_summary_df: pd.DataFrame,
    region_overlap_df: pd.DataFrame,
    config: HypothesisGenerationConfig,
) -> HypothesisResult:
    if not config.enabled:
        return HypothesisResult(pd.DataFrame(), "# Hypotheses\n\nHypothesis generation was disabled.\n", {})

    rows: list[dict[str, object]] = []
    evidence: dict[str, object] = {}

    if "shared_tolerance_pattern" in config.categories and not allele_tolerance_df.empty:
        sorted_df = allele_tolerance_df.sort_values("mean_abs_delta_total_contacts_vs_wt")
        if len(sorted_df) >= config.min_supporting_alleles:
            pair = sorted_df.head(2)["allele_name"].tolist()
            rows.append(
                _hypothesis_row(
                    hypothesis_id="shared_tolerance_pattern_1",
                    category="shared_tolerance_pattern",
                    statement=(
                        f"{pair[0]} and {pair[1]} show similarly low mean absolute contact disruption across the current mutant panel."
                    ),
                    supporting_metrics="mean_abs_delta_total_contacts_vs_wt",
                    supporting_tables="allele_tolerance_fingerprint.csv",
                    supporting_figures="allele_similarity_heatmap.png",
                    confidence_level="exploratory",
                    caveats="This reflects only the available prediction panel and should not be treated as functional equivalence.",
                )
            )
            evidence["shared_tolerance_pattern"] = sorted_df.head(2).to_dict(orient="records")

    if "anchor_disruption_pattern" in config.categories and not fingerprint_df.empty:
        anchor_df = fingerprint_df.dropna(subset=["delta_contacts_at_anchor_positions_vs_wt"])
        if len(anchor_df) >= config.min_supporting_variants:
            disruptive = anchor_df.nsmallest(config.min_supporting_variants, "delta_contacts_at_anchor_positions_vs_wt")
            rows.append(
                _hypothesis_row(
                    hypothesis_id="anchor_disruption_pattern_1",
                    category="anchor_disruption_pattern",
                    statement="Several mutants in the current panel are associated with reduced anchor-position contact counts relative to WT.",
                    supporting_metrics="delta_contacts_at_anchor_positions_vs_wt",
                    supporting_tables="tolerance_fingerprint.csv",
                    supporting_figures="delta_contacts_vs_wt_by_mutant.png",
                    confidence_level="exploratory",
                    caveats="Anchor interpretation depends on the configured anchor positions and the available structures.",
                )
            )
            evidence["anchor_disruption_pattern"] = disruptive.to_dict(orient="records")

    if "allele_specific_contact_network" in config.categories and not pocket_signature_summary_df.empty:
        distinctive = pocket_signature_summary_df.sort_values("num_unique_contacting_residues", ascending=False).head(1)
        if not distinctive.empty:
            rows.append(
                _hypothesis_row(
                    hypothesis_id="allele_specific_contact_network_1",
                    category="allele_specific_contact_network",
                    statement=(
                        f"{distinctive.iloc[0]['allele_name']} shows the broadest raw contacting-residue footprint in the current structural panel."
                    ),
                    supporting_metrics="num_unique_contacting_residues;contact_density_score",
                    supporting_tables="pocket_signature_summary.csv",
                    supporting_figures="pocket_overlap_heatmap.png",
                    confidence_level="descriptive",
                    caveats="Raw contacting-residue breadth does not imply broader biological permissiveness by itself.",
                )
            )
            evidence["allele_specific_contact_network"] = distinctive.to_dict(orient="records")

    if "pocket_region_sensitivity" in config.categories and not region_overlap_df.empty:
        focused = region_overlap_df.sort_values("allele_count").head(1)
        rows.append(
            _hypothesis_row(
                hypothesis_id="pocket_region_sensitivity_1",
                category="pocket_region_sensitivity",
                statement=(
                    f"Pocket region {focused.iloc[0]['pocket_region']} appears unevenly represented across alleles in the current contact-derived region mapping."
                ),
                supporting_metrics="allele_count",
                supporting_tables="region_overlap_summary.csv",
                supporting_figures="position_sensitivity_by_allele.png",
                confidence_level="low",
                caveats="Region-level comparisons are only as reliable as the user-supplied residue-to-region mapping.",
            )
        )
        evidence["pocket_region_sensitivity"] = focused.to_dict(orient="records")

    if not cross_allele_summary_df.empty:
        evidence["cross_allele_summary"] = cross_allele_summary_df.to_dict(orient="records")

    hypotheses_df = pd.DataFrame(rows)
    markdown = _build_markdown(hypotheses_df)
    return HypothesisResult(hypotheses_df, markdown, evidence)


def write_hypothesis_evidence(evidence: dict[str, object], output_path: Path) -> None:
    output_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def _hypothesis_row(**kwargs) -> dict[str, object]:
    return {
        "status": "exploratory",
        **kwargs,
    }


def _build_markdown(hypotheses_df: pd.DataFrame) -> str:
    lines = ["# Exploratory Hypotheses", ""]
    if hypotheses_df.empty:
        lines.append("No hypothesis rows were generated from the available outputs.")
        return "\n".join(lines)
    for row in hypotheses_df.to_dict(orient="records"):
        lines.append(f"## {row['hypothesis_id']}")
        lines.append("")
        lines.append(f"- Category: {row['category']}")
        lines.append(f"- Statement: {row['statement']}")
        lines.append(f"- Confidence: {row['confidence_level']}")
        lines.append(f"- Caveats: {row['caveats']}")
        lines.append("")
    return "\n".join(lines)
