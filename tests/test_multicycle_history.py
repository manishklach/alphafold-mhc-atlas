from pathlib import Path
import textwrap

import pandas as pd

from src.multicycle_history import summarize_multicycle_history


def test_multicycle_history_tracks_stable_and_churny_items(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "review").mkdir(parents=True)
    (project / "analysis").mkdir(parents=True)
    week1 = project / "review_packets" / "week_1" / "review_packet_tables"
    week2 = project / "review_packets" / "week_2" / "review_packet_tables"
    week1.mkdir(parents=True)
    week2.mkdir(parents=True)

    pd.DataFrame(
        [
            {"entity_id": "v_stable", "review_status": "shortlisted", "rationale": "keep reviewing"},
            {"entity_id": "v_churn", "review_status": "uncertain", "rationale": "needs more evidence"},
        ]
    ).to_csv(week1 / "shortlist.csv", index=False)
    pd.DataFrame([{"question_id": "q1", "question_text": "Question one"}]).to_csv(week1 / "open_questions.csv", index=False)
    pd.DataFrame(columns=["entity_type", "entity_id", "action_type", "status"]).to_csv(week1 / "next_action_table.csv", index=False)
    pd.DataFrame(
        [
            {"entity_id": "v_stable", "review_status": "shortlisted", "rationale": "still useful"},
            {"entity_id": "v_churn", "review_status": "rejected", "rationale": "drop for now"},
        ]
    ).to_csv(week2 / "shortlist.csv", index=False)
    pd.DataFrame([{"question_id": "q1", "question_text": "Question one"}]).to_csv(week2 / "open_questions.csv", index=False)
    pd.DataFrame(columns=["entity_type", "entity_id", "action_type", "status"]).to_csv(week2 / "next_action_table.csv", index=False)
    pd.DataFrame(
        [
            {"entity_id": "v_stable", "review_status": "shortlisted", "rationale": "carry forward"},
            {"entity_id": "v_churn", "review_status": "shortlisted", "rationale": "reintroduced"},
        ]
    ).to_csv(project / "review" / "shortlist.csv", index=False)
    pd.DataFrame([{"question_id": "q1", "question_text": "Question one"}]).to_csv(project / "analysis" / "open_questions.csv", index=False)
    pd.DataFrame(columns=["entity_type", "entity_id", "action_type", "status"]).to_csv(project / "analysis" / "next_action_table.csv", index=False)

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

    outputs = summarize_multicycle_history(workspace)
    summary_df = pd.read_csv(outputs["multicycle_decision_summary.csv"])
    stable_df = pd.read_csv(outputs["stable_shortlist_items.csv"])
    churn_df = pd.read_csv(outputs["decision_churn.csv"])

    stable_row = summary_df[summary_df["entity_id"] == "v_stable"].iloc[0]
    churn_row = summary_df[summary_df["entity_id"] == "v_churn"].iloc[0]
    assert int(stable_row["num_cycles_seen"]) >= 3
    assert float(stable_row["churn_score"]) == 0.0
    assert "v_stable" in stable_df["entity_id"].astype(str).tolist()
    assert float(churn_row["churn_score"]) > 0.0
    assert "v_churn" in churn_df["entity_id"].astype(str).tolist()
