from core.scoring.prioritization import rank_candidates


def test_rank_candidates_orders_by_change_and_flags_low_confidence() -> None:
    comparison_results = [
        {
            "candidate_id": "mut_low_conf",
            "structure_shift_score": 2.5,
            "residue_changes": [
                {"change_type": "mutated"},
                {"change_type": "shifted"},
            ],
            "confidence_summary": {"mean_confidence": 62.0, "source": "bfactor_as_plddt_proxy"},
            "flags": ["chains_added:B"],
        },
        {
            "candidate_id": "mut_high_conf",
            "structure_shift_score": 1.2,
            "residue_changes": [
                {"change_type": "mutated"},
            ],
            "confidence_summary": {"mean_confidence": 88.0, "source": "bfactor_as_plddt_proxy"},
            "flags": [],
        },
    ]

    ranked = rank_candidates(comparison_results)

    assert ranked[0]["candidate_id"] == "mut_low_conf"
    assert ranked[0]["priority_score"] > ranked[1]["priority_score"]
    assert ranked[0]["priority_label"] == "LOW"
    assert "low_confidence" in ranked[0]["flags"]
    assert "chains_added:B" in ranked[0]["flags"]
    assert "Significant structural change observed" in ranked[0]["explanation"]
    assert "Confidence is low, so this result should be interpreted cautiously." in ranked[0]["explanation"]
