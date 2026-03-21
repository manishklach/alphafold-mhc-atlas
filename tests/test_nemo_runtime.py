from core.runtime.nemo_runtime import NemoRuntime


def test_nemo_runtime_success_path_returns_logs_and_task_id() -> None:
    runtime = NemoRuntime()

    result = runtime.run(
        {
            "candidate_id": "nemo_success",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        }
    )

    assert result["status"] == "success"
    assert result["task_id"]
    assert isinstance(result["logs"], list)
    assert result["logs"]
    assert result["result"]["final_output"]["ranking"]["candidate_id"] == "nemo_success"


def test_nemo_runtime_blocked_path_when_required_input_missing() -> None:
    runtime = NemoRuntime()

    result = runtime.run(
        {
            "candidate_id": "nemo_blocked",
            "wt_file": "data/wt.pdb",
            "mutant_file": "",
        }
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "missing required input"
    assert result["logs"][-1]["status"] == "blocked"


def test_nemo_runtime_error_path_for_bad_file() -> None:
    runtime = NemoRuntime()

    result = runtime.run(
        {
            "candidate_id": "nemo_error",
            "wt_file": "data/does_not_exist.pdb",
            "mutant_file": "data/mut2.pdb",
        }
    )

    assert result["status"] == "error"
    assert "does_not_exist.pdb" in result["error"]
    assert any(log["status"] == "failure" for log in result["logs"])
