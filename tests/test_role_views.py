from pathlib import Path
import shutil

from src.action_planning import build_action_plan
from src.project_history import build_project_history
from src.role_views import export_role_views


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/pilot_review_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_role_view_exports_include_scope(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    build_project_history(project)
    build_action_plan(project)
    paths = export_role_views(project)
    assert "Conservative by design" in paths["manager"].read_text(encoding="utf-8")
    assert "exploratory structural analysis" in paths["scientist"].read_text(encoding="utf-8")
