from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any
from .package_schema import WorkflowBundle

def load_workflow_bundles(bundles_path: Path) -> list[WorkflowBundle]:
    if not bundles_path.exists():
        return []
    with open(bundles_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        return []
    bundles = []
    for b in data:
        bundles.append(WorkflowBundle(
            name=b['name'],
            description=b['description'],
            objective=b['objective'],
            commands=b.get('commands', []),
            expected_inputs=b.get('expected_inputs', []),
            expected_outputs=b.get('expected_outputs', []),
            caveats=b.get('caveats', []),
            recommended_roles=b.get('recommended_roles', []),
            eval_questions=b.get('eval_questions', [])
        ))
    return bundles

def get_workflow_bundle(bundles: list[WorkflowBundle], name: str) -> WorkflowBundle | None:
    for b in bundles:
        if b.name == name:
            return b
    return None
