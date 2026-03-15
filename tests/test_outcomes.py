from pathlib import Path
import textwrap

import pandas as pd

from src.outcomes import import_outcomes, summarize_outcomes


def test_outcomes_import_and_summary(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "review").mkdir(parents=True)
    (project / "analysis").mkdir(parents=True)
    (project / "review" / "shortlist.csv").write_text(
        "entity_id,review_status,rationale\nv1,shortlisted,stronger evidence\n",
        encoding="utf-8",
    )
    (project / "analysis" / "open_questions.csv").write_text("question_id,question_text\nq1,Need more support\n", encoding="utf-8")
    (project / "analysis" / "next_action_table.csv").write_text(
        "entity_type,entity_id,action_type,status,rationale\nvariant,v1,review_in_meeting,open,Discuss in meeting\n",
        encoding="utf-8",
    )

    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        textwrap.dedent(
            f"""
            workspace:
              workspace_id: ws_1
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

    outcome_file = tmp_path / "outcomes.csv"
    outcome_file.write_text(
        "\n".join(
            [
                "outcome_id,entity_type,entity_id,project_id,workspace_id,cycle_id,outcome_class,outcome_source,outcome_timestamp,outcome_notes,linked_artifacts,reviewer_or_owner,confidence_in_outcome_context,not_model_truth_flag",
                "o1,shortlist_item,v1,proj_a,ws_1,week_2,tested_followup,internal_review,2026-01-15T00:00:00+00:00,Followed up,review/shortlist.csv,scientist,moderate,true",
            ]
        ),
        encoding="utf-8",
    )

    import_path = import_outcomes(workspace, outcome_file)
    outputs = summarize_outcomes(workspace)
    summary_df = pd.read_csv(outputs["outcomes_summary.csv"])
    outcome_aware_df = pd.read_csv(outputs["outcome_aware_decision_summary.csv"])

    assert import_path.exists()
    assert "tested_followup" in summary_df["outcome_class"].astype(str).tolist()
    assert "v1" in outcome_aware_df["entity_id"].astype(str).tolist()
