from __future__ import annotations
from pathlib import Path
from .package_schema import WorkflowBundle
from .workflow_bundles import load_workflow_bundles

def get_default_workflow_bundles_path() -> Path:
    return Path(__file__).parent / "resources" / "data" / "workflow_bundles.yaml"

def get_customer_workflow_manager():
    path = get_default_workflow_bundles_path()
    return load_workflow_bundles(path)
