from pathlib import Path
import shutil

import pandas as pd

from src.checklists import load_checklist_templates, run_checklist


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/small_project/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_checklist_template_loads() -> None:
    payload = load_checklist_templates()
    assert payload["templates"]


def test_run_checklist_writes_rows(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    path = run_checklist(project, "panel_design_review", reviewer="alice")
    df = pd.read_csv(path)
    assert not df.empty
    assert set(df["status"]) == {"pending"}
