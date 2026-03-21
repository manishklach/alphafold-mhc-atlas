from fastapi.testclient import TestClient

from apps.api.main import app


def test_api_has_expected_routes() -> None:
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/parse" in paths
    assert "/compare" in paths
    assert "/rank" in paths
    assert "/pipeline" in paths


def test_api_flow_endpoints_return_json() -> None:
    client = TestClient(app)
    parse_response = client.post(
        "/parse",
        json={"file_path": "data/demo_structures/wt_example.pdb"},
    )
    assert parse_response.status_code == 200
    parsed = parse_response.json()
    assert parsed["chains"] == ["A"]

    compare_response = client.post(
        "/compare",
        json={
            "wt_file": "data/demo_structures/wt_example.pdb",
            "mutant_file": "data/demo_structures/mutant_example_a.pdb",
        },
    )
    assert compare_response.status_code == 200
    comparison = compare_response.json()
    assert "avg_shift" in comparison
    assert "flags" in comparison

    rank_response = client.post(
        "/rank",
        json={
            "comparisons": [
                {
                    "candidate_id": "api_candidate_1",
                    "comparison": comparison,
                }
            ]
        },
    )
    assert rank_response.status_code == 200
    ranked = rank_response.json()
    assert ranked["ranked_candidates"][0]["candidate_id"] == "api_candidate_1"
    assert "priority_label" in ranked["ranked_candidates"][0]

    pipeline_response = client.post(
        "/pipeline",
        json={
            "wt_file": "data/demo_structures/wt_example.pdb",
            "mutant_file": "data/demo_structures/mutant_example_a.pdb",
            "candidate_id": "api_candidate_1",
        },
    )
    assert pipeline_response.status_code == 200
    pipeline = pipeline_response.json()
    assert pipeline["candidate_id"] == "api_candidate_1"
    assert pipeline["ranking"]["candidate_id"] == "api_candidate_1"
    assert pipeline["decision"]["candidate_id"] == "api_candidate_1"
    assert pipeline["report_path"].endswith("api_candidate_1.md")
