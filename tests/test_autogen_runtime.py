from core.runtime.autogen_runtime import AutoGenRuntime


def test_autogen_runtime_success_path_returns_agent_trace() -> None:
    runtime = AutoGenRuntime()

    result = runtime.run(
        {
            "candidate_id": "autogen_demo",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        }
    )

    assert result["status"] == "success"
    assert result["task_id"]
    assert result["agent_trace"] == [
        "StructureAgent",
        "ComparisonAgent",
        "PrioritizationAgent",
        "ReviewAgent",
    ]
    assert result["result"]["final_output"]["ranking"]["candidate_id"] == "autogen_demo"
