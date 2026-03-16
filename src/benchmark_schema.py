from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .resource_paths import repo_or_resource_path


@dataclass(frozen=True)
class BenchmarkTemplate:
    benchmark_id: str
    label: str
    description: str
    data_source: str
    schema_version: float
    columns: dict[str, str] = field(default_factory=dict)
    outcome_mapping: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "label": self.label,
            "description": self.description,
            "data_source": self.data_source,
            "schema_version": self.schema_version,
            "columns": self.columns,
            "outcome_mapping": self.outcome_mapping,
        }


def load_benchmark_templates(path: Path | None = None) -> list[BenchmarkTemplate]:
    if path is None:
        path = repo_or_resource_path("data", "benchmark_templates.yaml")
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("benchmarks", []) if isinstance(payload, dict) else []
    return [BenchmarkTemplate(**t) for t in templates if isinstance(t, dict)]


def get_benchmark_template(benchmark_id: str) -> BenchmarkTemplate:
    templates = load_benchmark_templates()
    for t in templates:
        if t.benchmark_id == benchmark_id:
            return t
    raise ValueError(f"Benchmark template '{benchmark_id}' not found.")
