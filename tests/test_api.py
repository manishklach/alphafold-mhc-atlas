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
