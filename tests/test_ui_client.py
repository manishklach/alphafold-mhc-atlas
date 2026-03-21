import json
from unittest.mock import patch

from apps.ui.app import _api_request


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
