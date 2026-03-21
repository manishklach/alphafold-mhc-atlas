from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app


def test_pipeline_golden_path_returns_low_priority_with_confidence_drop(tmp_path: Path) -> None:
    wt_path = tmp_path / "wt.pdb"
    mutant_path = tmp_path / "mutant.pdb"

    wt_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      11.000  13.000   8.500  1.00 88.00           N",
                "ATOM      2  CA  ALA A   1      12.400  13.100   8.700  1.00 86.00           C",
                "ATOM      3  C   ALA A   1      12.900  14.500   8.300  1.00 85.00           C",
                "ATOM      4  O   ALA A   1      12.300  15.500   8.600  1.00 84.00           O",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )
    mutant_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   SER A   1      11.400  13.200   8.700  1.00 74.00           N",
                "ATOM      2  CA  SER A   1      13.000  13.500   9.000  1.00 72.00           C",
                "ATOM      3  C   SER A   1      13.400  14.900   8.600  1.00 70.00           C",
                "ATOM      4  O   SER A   1      12.700  15.900   8.900  1.00 68.00           O",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.post(
        "/pipeline",
        json={
            "wt_file": str(wt_path),
            "mutant_file": str(mutant_path),
            "candidate_id": "golden_demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert 0.7 <= payload["comparison"]["avg_shift"] <= 0.9
    assert payload["ranking"]["priority_label"] == "LOW"
    assert "confidence_drop" in payload["ranking"]["flags"]
    assert payload["ranking"]["explanation"]


def test_pipeline_identical_structures_returns_zero_shift_and_low_priority(tmp_path: Path) -> None:
    wt_path = tmp_path / "wt_identical.pdb"
    mutant_path = tmp_path / "mutant_identical.pdb"
    structure_text = "\n".join(
        [
            "ATOM      1  N   ALA A   1      11.000  13.000   8.500  1.00 88.00           N",
            "ATOM      2  CA  ALA A   1      12.400  13.100   8.700  1.00 86.00           C",
            "ATOM      3  C   ALA A   1      12.900  14.500   8.300  1.00 85.00           C",
            "ATOM      4  O   ALA A   1      12.300  15.500   8.600  1.00 84.00           O",
            "TER",
            "END",
        ]
    )
    wt_path.write_text(structure_text, encoding="utf-8")
    mutant_path.write_text(structure_text, encoding="utf-8")

    client = TestClient(app)
    response = client.post(
        "/pipeline",
        json={
            "wt_file": str(wt_path),
            "mutant_file": str(mutant_path),
            "candidate_id": "identical_demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["comparison"]["avg_shift"] == 0.0
    assert payload["comparison"]["max_shift"] == 0.0
    assert payload["ranking"]["priority_label"] == "LOW"


def test_pipeline_extreme_shift_returns_high_priority(tmp_path: Path) -> None:
    wt_path = tmp_path / "wt_extreme.pdb"
    mutant_path = tmp_path / "mutant_extreme.pdb"

    wt_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 90.00           N",
                "ATOM      2  CA  ALA A   1      11.000  10.000  10.000  1.00 90.00           C",
                "ATOM      3  C   ALA A   1      12.000  10.000  10.000  1.00 90.00           C",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )
    mutant_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 90.00           N",
                "ATOM      2  CA  ALA A   1      15.500  10.000  10.000  1.00 90.00           C",
                "ATOM      3  C   ALA A   1      16.500  10.000  10.000  1.00 90.00           C",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.post(
        "/pipeline",
        json={
            "wt_file": str(wt_path),
            "mutant_file": str(mutant_path),
            "candidate_id": "extreme_demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["comparison"]["avg_shift"] > 4.0
    assert payload["ranking"]["priority_label"] == "HIGH"
