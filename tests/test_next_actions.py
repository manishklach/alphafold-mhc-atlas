from pathlib import Path
import shutil

import pandas as pd

from src.next_actions import build_next_actions
from src.open_questions import build_open_questions


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/pilot_review_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_next_actions_and_open_questions_build(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    next_path = build_next_actions(project)
    open_path = build_open_questions(project)
    next_df = pd.read_csv(next_path)
    open_df = pd.read_csv(open_path)
    assert not next_df.empty
    assert not open_df.empty
