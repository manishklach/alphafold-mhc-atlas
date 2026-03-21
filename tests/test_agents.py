from pathlib import Path

from agents.comparison_agent import run as run_comparison
from agents.comparison_agent import run_comparison_agent
from agents.prioritization_agent import run as run_prioritization
from agents.prioritization_agent import run_prioritization_agent
from agents.review_agent import run as run_review
from agents.review_agent import run_review_agent
from agents.structure_agent import run as run_structure
from agents.structure_agent import run_structure_agent


def test_agents_wrap_underlying_modules(tmp_path: Path) -> None:
    pdb_path = tmp_path / "example.pdb"
    pdb_path.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      11.104  13.207   8.560  1.00 85.00           N",
                "ATOM      2  CA  ALA A   1      12.560  13.100   8.770  1.00 84.00           C",
                "ATOM      3  C   ALA A   1      13.028  11.658   8.991  1.00 83.00           C",
                "TER",
                "END",
            ]
        ),
        encoding="utf-8",
    )

    structure_result = run_structure_agent(pdb_path)
    mutant_structure = {
        "chains": ["A"],
        "residues": [
            {
                "residue_id": "A:1",
                "chain_id": "A",
                "residue_name": "SER",
                "residue_number": 1,
            }
        ],
        "coordinates": [{"residue_id": "A:1", "chain_id": "A", "residue_name": "SER", "residue_number": 1, "x": 12.0, "y": 13.0, "z": 9.0}],
        "confidence_summary": {"avg": 65.0, "min": 65.0, "max": 65.0},
    }

    comparison_result = run_comparison_agent(structure_result["output"], mutant_structure)
    prioritization_result = run_prioritization_agent(
        [
            {
                "candidate_id": "candidate_1",
                "comparison": comparison_result["output"],
            }
        ]
    )
    review_result = run_review_agent(prioritization_result["output"])

    assert structure_result["agent"] == "structure_agent"
    assert comparison_result["agent"] == "comparison_agent"
    assert prioritization_result["agent"] == "prioritization_agent"
    assert review_result["agent"] == "review_agent"
    assert review_result["output"]["summary"]["num_candidates"] == 1
    assert run_structure({"structure_path": pdb_path})["agent"] == "structure_agent"
    assert run_comparison({"wt_structure": structure_result["output"], "mutant_structure": mutant_structure})["agent"] == "comparison_agent"
    assert run_prioritization({"comparison_results": [{"candidate_id": "candidate_1", "comparison": comparison_result["output"]}]})["agent"] == "prioritization_agent"
    assert run_review({"ranked_candidates": prioritization_result["output"]})["agent"] == "review_agent"
