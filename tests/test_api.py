from fastapi.testclient import TestClient

from apps.api.main import app


def test_pipeline_returns_candidate_score_and_explanation() -> None:
    client = TestClient(app)

    response = client.post(
        "/pipeline",
        json={
            "wt_file": "data/demo_structures/wt_example.pdb",
            "mutant_file": "data/demo_structures/mutant_example_a.pdb",
            "candidate_id": "demo_api",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "demo_api"
    assert "priority_score" in payload["ranking"]
    assert "explanation" in payload["ranking"]


def test_batch_pipeline_returns_sorted_results_and_candidate_errors() -> None:
    client = TestClient(app)

    response = client.post(
        "/batch_pipeline",
        json={
            "candidates": [
                {
                    "candidate_id": "batch_high",
                    "wt_file": "data/demo_structures/wt_example.pdb",
                    "mutant_file": "data/demo_structures/mutant_example_b.pdb",
                },
                {
                    "candidate_id": "batch_low",
                    "wt_file": "data/demo_structures/wt_example.pdb",
                    "mutant_file": "data/demo_structures/mutant_example_a.pdb",
                },
                {
                    "candidate_id": "batch_error",
                    "wt_file": "data/demo_structures/wt_example.pdb",
                    "mutant_file": "data/does_not_exist.pdb",
                },
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()
    results = payload["results"]
    top_candidates = payload["top_candidates"]

    assert len(results) == 3
    assert top_candidates
    assert top_candidates[0]["priority_score"] >= top_candidates[-1]["priority_score"]
    assert results[0]["candidate_id"] == "batch_high"
    assert results[1]["candidate_id"] == "batch_low"
    assert "error" not in results[0]
    assert "error" not in results[1]
    assert results[2]["candidate_id"] == "batch_error"
    assert "error" in results[2]
    assert "priority_score" not in results[2] or results[2]["priority_score"] is None


def test_pipeline_nemo_runtime_includes_runtime_metadata() -> None:
    client = TestClient(app)

    response = client.post(
        "/pipeline",
        json={
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
            "candidate_id": "demo_nemo",
            "runtime": "nemo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "demo_nemo"
    assert payload["task_id"]
    assert isinstance(payload["logs"], list)
    assert "warnings" in payload


def test_batch_pipeline_nemo_runtime_includes_candidate_runtime_summaries() -> None:
    client = TestClient(app)

    response = client.post(
        "/batch_pipeline",
        json={
            "runtime": "nemo",
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
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["candidate_id"] == "mut2"
    assert "task_id" in payload["results"][0]
    assert "log_summary" in payload["results"][0]


def test_report_endpoint_returns_markdown_report_content() -> None:
    client = TestClient(app)

    pipeline_response = client.post(
        "/pipeline",
        json={
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
            "candidate_id": "report_demo",
        },
    )
    assert pipeline_response.status_code == 200

    report_response = client.get("/report", params={"candidate_id": "report_demo"})
    assert report_response.status_code == 200
    payload = report_response.json()
    assert payload["file_name"] == "report_demo.md"
    assert "# MHC Atlas Decision Report" in payload["content"]
