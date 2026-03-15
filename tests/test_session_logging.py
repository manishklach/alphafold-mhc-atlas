from pathlib import Path
import shutil

import pandas as pd

from src.session_logging import log_session_action, start_session


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/small_project/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_session_logging_writes_summary(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    session = start_session(project, reviewer="alice")
    log_session_action(project, session["session_id"], "project_loaded", {"project": "demo"})
    assert (project / "review" / "session_log.jsonl").exists()
    action_df = pd.read_csv(project / "review" / "action_summary.csv")
    assert "project_loaded" in action_df["action_type"].tolist()
