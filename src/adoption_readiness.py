from __future__ import annotations
import csv
from pathlib import Path
from typing import Any
from .package_schema import ConversionArtifact

def load_adoption_readiness(path: Path) -> list[ConversionArtifact]:
    if not path.exists():
        return []
    artifacts = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            artifacts.append(ConversionArtifact(
                pilot_id=row["pilot_id"],
                workflows_tried=row["workflows_tried"].split(";"),
                useful_artifacts=row["useful_artifacts"].split(";"),
                persisting_friction=row["persisting_friction"].split(";"),
                next_steps=row["next_steps"].split(";"),
                readiness_score=float(row["readiness_score"])
            ))
    return artifacts

def summarize_adoption_readiness(artifacts: list[ConversionArtifact]) -> dict[str, Any]:
    if not artifacts:
        return {}
    avg_score = sum(a.readiness_score for a in artifacts) / len(artifacts)
    return {
        "average_readiness_score": avg_score,
        "total_pilots": len(artifacts),
        "common_friction_points": _get_common_items([a.persisting_friction for a in artifacts]),
        "most_useful_artifacts": _get_common_items([a.useful_artifacts for a in artifacts])
    }

def _get_common_items(item_lists: list[list[str]]) -> list[str]:
    counts = {}
    for items in item_lists:
        for item in items:
            if not item: continue
            counts[item] = counts.get(item, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [item for item, count in sorted_items[:5]]
