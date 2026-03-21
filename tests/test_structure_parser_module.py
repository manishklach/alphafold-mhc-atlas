from pathlib import Path

from biology.parsers.structure_parser import parse_structure_file


def test_parse_structure_file_returns_json_ready_summary(tmp_path: Path) -> None:
    pdb_path = tmp_path / "example.pdb"
    pdb_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      11.104  13.207   8.560  1.00 85.00           N",
                "ATOM      2  CA  ALA A   1      12.560  13.100   8.770  1.00 84.00           C",
                "ATOM      3  C   ALA A   1      13.028  11.658   8.991  1.00 83.00           C",
                "ATOM      4  N   GLY B   2       9.000  10.000   7.000  1.00 76.00           N",
                "ATOM      5  CA  GLY B   2       8.200   9.100   6.200  1.00 75.00           C",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    payload = parse_structure_file(pdb_path)

    assert payload["chains"] == ["A", "B"]
    assert len(payload["residues"]) == 2
    assert payload["residues"][0]["chain_id"] == "A"
    assert payload["residues"][0]["residue_name"] == "ALA"
    assert payload["residues"][0]["residue_id"] == "A:1"
    assert payload["coordinates"][0]["x"] == 12.56
    assert payload["coordinates"][0]["y"] == 13.1
    assert payload["confidence_summary"] == {"avg": 79.75, "min": 75.5, "max": 84.0}
