import json
from unittest.mock import patch

import pytest

from apps.ui.app import _api_request, _build_batch_display_rows, _parse_batch_csv, _runtime_value


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
    assert [row["rank"] for row in rows] == [1, 2, 3]
    assert rows[0]["_is_top_candidate"] is True
    assert rows[1]["_is_top_candidate"] is True
    assert rows[2]["_is_top_candidate"] is True
    assert rows[0]["_is_top_one"] is True
    assert rows[0]["flags"] == "x"


def test_runtime_value_maps_governed_mode_to_nemo() -> None:
    assert _runtime_value("Local") == "local"
    assert _runtime_value("Nemo (Governed)") == "nemo"


def test_parse_batch_csv_returns_candidate_rows() -> None:
    rows = _parse_batch_csv("candidate_id,wt_file,mutant_file\nmut1,data/wt.pdb,data/mut1.pdb\n")
    assert rows == [
        {
            "candidate_id": "mut1",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut1.pdb",
        }
    ]


def test_parse_batch_csv_validates_required_columns() -> None:
    with pytest.raises(ValueError, match="CSV must contain"):
        _parse_batch_csv("candidate_id,wt_file\nmut1,data/wt.pdb\n")
