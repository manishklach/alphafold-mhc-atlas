from pathlib import Path
import textwrap

import pandas as pd

from src.recurring_patterns import build_recurring_patterns


def test_recurring_patterns_workspace_summary(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "analysis").mkdir(parents=True)
    (project / "review").mkdir(parents=True)
    (project / "analysis" / "open_questions.csv").write_text(
        "question_id,category,question_text\nq1,insufficient_evidence,Should we trust v1?\nq2,insufficient_evidence,Should we trust v1?\n",
        encoding="utf-8",
    )
    (project / "analysis" / "next_action_table.csv").write_text(
        "entity_type,entity_id,action_type,priority_level,rationale,supporting_artifacts,owner_role_suggestion,status\nvariant,v1,review_in_meeting,high,Discuss,current,manager,open\n",
        encoding="utf-8",
    )
    (project / "review" / "shortlist.csv").write_text(
        "entity_id,uncertainty_level\nv1,high\n",
        encoding="utf-8",
    )
    (project / "analysis" / "priority_uncertainty_table.csv").write_text(
        "variant_id,ranking_mode,uncertainty_level\nv1,disruptive_mutations,high\n",
        encoding="utf-8",
    )
    (project / "review" / "feedback_log.csv").write_text(
        "feedback_id,concern_type\nf1,biological_caveat\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        textwrap.dedent(
            f"""
            workspace:
              workspace_id: test_ws
              name: Test Workspace
              description: Test
              output_dir: "{(tmp_path / 'workspace_outputs').as_posix()}"
              projects:
                - id: proj_a
                  path: "{project.as_posix()}"
            """
        ),
        encoding="utf-8",
    )

    outputs = build_recurring_patterns(workspace)
    questions_df = pd.read_csv(outputs["recurring_questions.csv"])
    patterns_df = pd.read_csv(outputs["recurring_patterns.csv"])
    assert "insufficient_evidence" in questions_df["category"].astype(str).tolist()
    assert "feedback_concern" in patterns_df["pattern_type"].astype(str).tolist()
