from __future__ import annotations

from pathlib import Path
from typing import Any

from biology.parsers.structure_parser import parse_structure


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    structure_path = input_data["structure_path"]
    parsed = parse_structure(structure_path)
    return {
        "agent": "structure_agent",
        "input": {"structure_path": str(structure_path)},
        "output": parsed,
    }


def run_structure_agent(structure_path: str | Path) -> dict[str, Any]:
    return run({"structure_path": structure_path})
