from pathlib import Path

from storage.db import get_candidates, get_decision_history, init_db, insert_candidate, save_decision


def test_storage_db_init_and_candidate_crud(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'mhc_atlas_os.db').as_posix()}"

    init_db(database_url)
    created = insert_candidate(
        candidate_id="candidate_001",
        metadata={"source": "unit_test"},
        status="queued",
        database_url=database_url,
    )
    candidates = get_candidates(database_url)

    assert created["candidate_id"] == "candidate_001"
    assert created["status"] == "queued"
    assert created["metadata"]["source"] == "unit_test"
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "candidate_001"

    decision = save_decision(
        candidate_id="candidate_001",
        priority_score=6.0,
        priority_label="MEDIUM",
        explanation="Moderate structural change observed.",
        flags=["confidence_drop"],
        database_url=database_url,
    )
    history = get_decision_history("candidate_001", database_url)

    assert decision["candidate_id"] == "candidate_001"
    assert decision["priority_label"] == "MEDIUM"
    assert history[0]["priority_score"] == 6.0
