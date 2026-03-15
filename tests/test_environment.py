import json
import subprocess
import sys
from pathlib import Path


def test_check_environment_script_runs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/check_environment.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["package"] == "mhc-atlas"
