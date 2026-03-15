from pathlib import Path

from src.workspace import load_workspace_config
from src.workspace_index import build_workspace_inventory


def test_workspace_config_loads() -> None:
    config = load_workspace_config("workspaces/demo_workspace.yaml")
    assert config.workspace_id == "pilot_workspace_01"
    assert len(config.projects) >= 2


def test_workspace_inventory_builds() -> None:
    inventory = build_workspace_inventory("workspaces/demo_workspace.yaml")
    assert inventory["projects"]
    assert inventory["summary"][0]["num_projects"] >= 2
