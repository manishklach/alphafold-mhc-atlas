import pandas as pd

from src.evidence_view import build_variant_evidence_bundle


def test_build_variant_evidence_bundle_collects_rows() -> None:
    tables = {
        "priority": pd.DataFrame([{"variant_id": "v1", "ranking_mode": "disruptive_mutations"}]),
        "priority_evidence": pd.DataFrame([{"variant_id": "v1", "evidence_name": "delta_total_contacts_vs_wt"}]),
        "priority_uncertainty": pd.DataFrame([{"variant_id": "v1", "uncertainty_level": "low"}]),
        "summary": pd.DataFrame([{"variant_id": "v1", "allele_name": "HLA-A*02:01"}]),
        "panel": pd.DataFrame([{"variant_id": "v1", "panel_id": "p1"}]),
        "cross_allele_summary": pd.DataFrame(),
    }

    bundle = build_variant_evidence_bundle("v1", tables)

    assert bundle["variant_id"] == "v1"
    assert len(bundle["priority_rows"]) == 1
    assert len(bundle["evidence_rows"]) == 1
