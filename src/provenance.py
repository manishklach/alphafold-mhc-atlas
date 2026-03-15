from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PIPELINE_VERSION = "phase5"


def build_provenance(config_path: Path, requirements_path: Path) -> dict[str, str]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "config_digest": _digest_file(config_path),
        "requirements_path": str(requirements_path),
        "requirements_digest": _digest_file(requirements_path),
        "git_commit": _git_commit_hash(config_path.parent),
    }


def _digest_file(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit_hash(repo_dir: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return "unavailable"
    return result.stdout.strip() or "unavailable"
