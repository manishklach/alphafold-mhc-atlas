import pytest

from core.orchestration.task_router import route_task


def test_route_task_single_analysis_uses_agent_pipeline() -> None:
    result = route_task(
        "single_analysis",
        {
            "candidate_id": "mut2",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        },
    )

    assert result["candidate_id"] == "mut2"
    assert result["status"] == "success"
    assert "final_output" in result
    assert result["final_output"]["ranking"]["priority_label"] == "HIGH"


def test_route_task_batch_analysis_returns_sorted_results() -> None:
    result = route_task(
        "batch_analysis",
        {
            "candidates": [
                {
                    "candidate_id": "mut1",
                    "wt_file": "data/wt.pdb",
                    "mutant_file": "data/mut1.pdb",
                },
                {
                    "candidate_id": "mut2",
                    "wt_file": "data/wt.pdb",
                    "mutant_file": "data/mut2.pdb",
                },
            ]
        },
    )

    assert result["task_type"] == "batch_analysis"
    assert result["status"] == "success"
    assert [item["candidate_id"] for item in result["results"][:2]] == ["mut2", "mut1"]
    assert result["top_candidates"][0]["candidate_id"] == "mut2"


def test_route_task_rejects_unknown_task_type() -> None:
    with pytest.raises(ValueError, match="Unsupported task_type"):
        route_task("unknown_task", {})
