from pathlib import Path
import shutil

import pandas as pd

from src.feedback import add_feedback
from src.feedback_schema import FeedbackEntry


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/cross_allele_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_add_feedback_creates_summary_files(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    add_feedback(
        project,
        FeedbackEntry(
            entity_type="variant",
            entity_id="demoA_pos2_A",
            reviewer_name="alice",
            reviewer_role="scientist",
            sentiment="mixed",
            usefulness_rating=4,
            clarity_rating=3,
            confidence_in_output="moderate",
            concern_type="biological_caveat",
            free_text_comment="Needs experimental caveat.",
            requested_followup="review shortlist",
            status="open",
        ),
    )
    assert (project / "review" / "feedback_log.csv").exists()
    assert (project / "review" / "feedback_summary.csv").exists()
    assert (project / "review" / "feedback_by_entity.csv").exists()
    assert (project / "review" / "feedback_digest.md").exists()
    summary_df = pd.read_csv(project / "review" / "feedback_summary.csv")
    assert "biological_caveat" in summary_df["concern_type"].tolist()
