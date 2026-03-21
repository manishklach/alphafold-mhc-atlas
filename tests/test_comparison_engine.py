from biology.comparisons.comparison_engine import compare_structures


def test_compare_structures_returns_requested_summary() -> None:
    wt = {
        "chains": ["A"],
        "residues": [
            {
                "residue_id": "A:1",
                "chain_id": "A",
                "residue_name": "ALA",
                "residue_number": 1,
            },
            {
                "residue_id": "A:2",
                "chain_id": "A",
                "residue_name": "GLY",
                "residue_number": 2,
            },
        ],
        "coordinates": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1, "x": 0.0, "y": 0.0, "z": 0.0},
            {"residue_id": "A:2", "chain_id": "A", "residue_name": "GLY", "residue_number": 2, "x": 2.0, "y": 0.0, "z": 0.0},
        ],
        "confidence_summary": {"avg": 85.0, "min": 80.0, "max": 90.0},
    }
    mutant = {
        "chains": ["A"],
        "residues": [
            {
                "residue_id": "A:1",
                "chain_id": "A",
                "residue_name": "SER",
                "residue_number": 1,
            },
            {
                "residue_id": "A:3",
                "chain_id": "A",
                "residue_name": "TYR",
                "residue_number": 3,
            },
        ],
        "coordinates": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "SER", "residue_number": 1, "x": 3.0, "y": 0.0, "z": 0.0},
            {"residue_id": "A:3", "chain_id": "A", "residue_name": "TYR", "residue_number": 3, "x": 5.0, "y": 0.0, "z": 0.0},
        ],
        "confidence_summary": {"avg": 70.0, "min": 65.0, "max": 75.0},
    }

    result = compare_structures(wt, mutant)

    assert result["avg_shift"] == 3.0
    assert result["max_shift"] == 3.0
    assert result["large_shift_count"] == 1
    assert result["confidence_delta"] == -15.0
    assert result["structure_shift_score"] == 3.0
    assert any(change["change_type"] == "mutated" for change in result["residue_changes"])
    assert any(change["change_type"] == "missing_in_mutant" for change in result["residue_changes"])
    assert any(change["change_type"] == "present_in_mutant_only" for change in result["residue_changes"])
    assert "high_structural_change" in result["flags"]
    assert "confidence_drop" in result["flags"]


def test_compare_structures_handles_missing_residues_without_crashing() -> None:
    wt = {
        "chains": ["A"],
        "residues": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1},
            {"residue_id": "A:2", "chain_id": "A", "residue_name": "GLY", "residue_number": 2},
        ],
        "coordinates": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1, "x": 0.0, "y": 0.0, "z": 0.0},
            {"residue_id": "A:2", "chain_id": "A", "residue_name": "GLY", "residue_number": 2, "x": 1.0, "y": 0.0, "z": 0.0},
        ],
        "confidence_summary": {"avg": 80.0, "min": 80.0, "max": 80.0},
    }
    mutant = {
        "chains": ["A"],
        "residues": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1},
        ],
        "coordinates": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1, "x": 0.0, "y": 0.0, "z": 0.0},
        ],
        "confidence_summary": {"avg": 80.0, "min": 80.0, "max": 80.0},
    }

    result = compare_structures(wt, mutant)

    assert result["avg_shift"] == 0.0
    assert any(change["change_type"] == "missing_in_mutant" for change in result["residue_changes"])


def test_compare_structures_skips_missing_coordinates_safely() -> None:
    wt = {
        "chains": ["A"],
        "residues": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1},
        ],
        "coordinates": [],
        "confidence_summary": {"avg": 80.0, "min": 80.0, "max": 80.0},
    }
    mutant = {
        "chains": ["A"],
        "residues": [
            {"residue_id": "A:1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1},
        ],
        "coordinates": [],
        "confidence_summary": {"avg": 80.0, "min": 80.0, "max": 80.0},
    }

    result = compare_structures(wt, mutant)

    assert result["avg_shift"] == 0.0
    assert result["max_shift"] == 0.0
    assert result["large_shift_count"] == 0
