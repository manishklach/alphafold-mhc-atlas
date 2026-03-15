from pathlib import Path
import shutil

from src.project_history import build_project_history


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/pilot_review_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_build_project_history_writes_outputs(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    path = build_project_history(project)
    assert path.exists()
    assert (project / "history" / "decision_history.csv").exists()
    assert (project / "history" / "status_timeline.csv").exists()
    assert (project / "history" / "change_summary.md").exists()
