from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.cli import _environment_payload


def main() -> None:
    print(json.dumps(_environment_payload(), indent=2))


if __name__ == "__main__":
    main()
