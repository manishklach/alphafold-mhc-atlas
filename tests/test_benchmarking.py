import pandas as pd

from src.benchmarking import run_benchmarking
from src.config import BenchmarkingConfig


def test_benchmarking_falls_back_to_internal_checks() -> None:
    summary_df = pd.DataFrame(
        [
            {"variant_id": "v1", "structure_path": None, "total_peptide_mhc_contacts": None, "local_variant_id": "WT"},
            {"variant_id": "v2", "structure_path": None, "total_peptide_mhc_contacts": None, "local_variant_id": "pos2_A"},
        ]
    )
    fingerprint_df = pd.DataFrame([{"variant_id": "v2"}])

    summary, details, reference, warnings = run_benchmarking(
        summary_df,
        fingerprint_df,
        BenchmarkingConfig(
            enabled=True,
            reference_structure_map=None,
            known_disruptive_variants_file=None,
            expected_anchor_positions=[2, 9],
        ),
    )

    assert not summary.empty
    assert not details.empty
    assert not warnings.empty
    assert reference.iloc[0]["benchmark_mode"] in {"reference_structure_comparison", "reference_comparison"}
