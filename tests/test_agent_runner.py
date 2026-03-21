from core.orchestration.agent_runner import run_agent_pipeline


def test_run_agent_pipeline_success_path_uses_all_stages() -> None:
    result = run_agent_pipeline(
        candidate_id="runner_demo",
        wt_file="data/wt.pdb",
        mutant_file="data/mut2.pdb",
    )

    assert result["candidate_id"] == "runner_demo"
    assert result["status"] == "success"
    assert set(result["stages"].keys()) == {
        "structure",
        "comparison",
        "prioritization",
        "policy",
        "review",
    }
    assert all(result["stages"][stage]["status"] == "success" for stage in result["stages"])
    assert all("duration_ms" in result["stages"][stage] for stage in result["stages"])
    assert result["total_duration_ms"] >= 0
    assert result["final_output"]["ranking"]["candidate_id"] == "runner_demo"
    assert result["final_output"]["review"]["summary"]["num_candidates"] == 1
    assert result["final_output"]["confidence_summary"]["wt_avg_confidence"] is not None
    assert result["final_output"]["confidence_summary"]["mutant_avg_confidence"] is not None
    assert "priority_label" in result["final_output"]["confidence_summary"]
    assert [entry["stage"] for entry in result["logs"]] == [
        "structure",
        "structure",
        "comparison",
        "comparison",
        "prioritization",
        "prioritization",
        "policy",
        "policy",
        "review",
        "review",
    ]
    assert result["logs"][-1]["status"] == "success"
    assert {"stage", "status", "message", "input_summary", "output_summary", "duration_ms"} <= set(
        result["logs"][-1].keys()
    )


def test_run_agent_pipeline_failure_path_returns_readable_error() -> None:
    result = run_agent_pipeline(
        candidate_id="runner_bad",
        wt_file="data/does_not_exist.pdb",
        mutant_file="data/mut2.pdb",
    )

    assert result["candidate_id"] == "runner_bad"
    assert result["status"] == "error"
    assert result["total_duration_ms"] >= 0
    assert "structure" in result["stages"]
    assert result["stages"]["structure"]["status"] == "error"
    assert "Failed to parse structures" in result["stages"]["structure"]["message"]
    assert result["logs"][-1]["stage"] == "structure"
    assert result["logs"][-1]["status"] == "failure"
    assert "does_not_exist.pdb" in result["logs"][-1]["message"]
    assert result["logs"][-1]["duration_ms"] >= 0
