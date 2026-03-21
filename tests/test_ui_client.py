import json
from unittest.mock import patch

from apps.ui.app import _api_request, _build_batch_display_rows


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def test_api_request_parses_json_response() -> None:
    with patch("apps.ui.app.request.urlopen", return_value=_FakeResponse({"status": "ok"})):
        payload = _api_request("GET", "/health")
    assert payload["status"] == "ok"


def test_build_batch_display_rows_sorts_and_marks_top_candidates() -> None:
    rows = _build_batch_display_rows(
        [
            {"candidate_id": "b", "priority_score": 2.0, "priority_label": "LOW", "flags": []},
            {"candidate_id": "a", "priority_score": 8.0, "priority_label": "HIGH", "flags": ["x"]},
            {"candidate_id": "c", "priority_score": 5.0, "priority_label": "MEDIUM", "flags": ["y"]},
            {"candidate_id": "bad", "error": "missing file", "flags": []},
        ]
    )

    assert [row["candidate_id"] for row in rows] == ["a", "c", "b"]
    assert rows[0]["_is_top_candidate"] is True
    assert rows[1]["_is_top_candidate"] is True
    assert rows[2]["_is_top_candidate"] is True
    assert rows[0]["flags"] == "x"
