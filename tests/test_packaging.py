from pathlib import Path
import tomllib


def test_pyproject_contains_console_script() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "mhc-atlas-os"
    assert data["project"]["scripts"]["mhc-atlas-os-api"] == "apps.api.main:run"
