from scripts.demo_showcase import run_demo_showcase


def test_run_demo_showcase_returns_single_batch_nemo_and_history() -> None:
    result = run_demo_showcase()

    assert result["single_result"]["status"] == "success"
    assert result["batch_results"]
    assert result["batch_results"][0]["final_output"]["ranking"]["candidate_id"] == "mut2"
    assert result["nemo_result"]["status"] == "success"
    assert isinstance(result["history"], list)
