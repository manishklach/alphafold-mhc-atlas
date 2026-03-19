from pathlib import Path
import json
import textwrap

import pandas as pd

from src.workflow_metrics import summarize_workflow_metrics


def test_workflow_metrics_handles_partial_data(tmp_path: Path) -> None:
    output_dir = tmp_path / "workspace_outputs"
    packet_dir = output_dir / "review_packets" / "week_1"
    packet_dir.mkdir(parents=True)
    (packet_dir / "review_packet_summary.json").write_text(
        json.dumps(
            {
                "workflow_template": "weekly_mutation_review",
                "num_projects": 1,
                "num_open_questions": 2,
                "num_next_actions": 4,
                "num_shortlist_items": 3,
            }
        ),
        encoding="utf-8",
    )
    project = tmp_path / "project_a"
    project.mkdir()
    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        textwrap.dedent(
            f"""
            workspace:
              workspace_id: ws_1
              name: Test Workspace
              description: Test
              output_dir: "{output_dir.as_posix()}"
              projects:
                - id: proj_a
                  path: "{project.as_posix()}"
            """
        ),
        encoding="utf-8",
    )

    outputs = summarize_workflow_metrics(workspace)
    cycle_df = pd.read_csv(outputs["cycle_operational_metrics.csv"])

    assert "weekly_mutation_review" in cycle_df["template_name"].astype(str).tolist()
    assert "unresolved_carryforward_ratio" in cycle_df.columns


def test_workflow_metrics_scope_outcomes_to_relevant_entities(tmp_path: Path) -> None:
    output_dir = tmp_path / "workspace_outputs"
    packet_dir = output_dir / "review_packets" / "week_1"
    tables_dir = packet_dir / "review_packet_tables"
    tables_dir.mkdir(parents=True)
    (packet_dir / "review_packet_summary.json").write_text(
        json.dumps(
            {
                "workflow_template": "weekly_mutation_review",
                "num_projects": 1,
                "num_open_questions": 1,
                "num_next_actions": 2,
                "num_shortlist_items": 1,
                "generated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame([{"entity_id": "v1", "review_status": "shortlisted"}]).to_csv(tables_dir / "shortlist.csv", index=False)
    pd.DataFrame([{"question_id": "q1", "question_text": "Need follow-up"}]).to_csv(tables_dir / "open_questions.csv", index=False)
    pd.DataFrame(
        [
            {"entity_type": "variant", "entity_id": "v1", "action_type": "review_in_meeting", "status": "done"},
            {"entity_type": "variant", "entity_id": "v2", "action_type": "review_in_meeting", "status": "open"},
        ]
    ).to_csv(tables_dir / "next_action_table.csv", index=False)

    project = tmp_path / "project_a"
    project.mkdir()
    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        textwrap.dedent(
            f"""
            workspace:
              workspace_id: ws_1
              name: Test Workspace
              description: Test
              output_dir: "{output_dir.as_posix()}"
              projects:
                - id: proj_a
                  path: "{project.as_posix()}"
            """
        ),
        encoding="utf-8",
    )
    program_memory = output_dir / "program_memory"
    program_memory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "outcome_id": "o1",
                "entity_type": "variant",
                "entity_id": "v1",
                "project_id": "proj_a",
                "workspace_id": "ws_1",
                "cycle_id": "week_1",
                "outcome_class": "tested_followup",
                "outcome_source": "internal_review",
                "outcome_timestamp": "2026-01-02T00:00:00+00:00",
                "outcome_notes": "",
                "linked_artifacts": "",
                "reviewer_or_owner": "scientist",
                "confidence_in_outcome_context": "moderate",
                "not_model_truth_flag": "true",
            },
            {
                "outcome_id": "o2",
                "entity_type": "panel",
                "entity_id": "panel_1",
                "project_id": "proj_a",
                "workspace_id": "ws_1",
                "cycle_id": "week_1",
                "outcome_class": "tested_followup",
                "outcome_source": "internal_review",
                "outcome_timestamp": "2026-01-02T00:00:00+00:00",
                "outcome_notes": "",
                "linked_artifacts": "",
                "reviewer_or_owner": "scientist",
                "confidence_in_outcome_context": "moderate",
                "not_model_truth_flag": "true",
            },
            {
                "outcome_id": "o3",
                "entity_type": "open_question",
                "entity_id": "q1",
                "project_id": "proj_a",
                "workspace_id": "ws_1",
                "cycle_id": "week_1",
                "outcome_class": "deprioritized",
                "outcome_source": "internal_review",
                "outcome_timestamp": "2026-01-02T00:00:00+00:00",
                "outcome_notes": "",
                "linked_artifacts": "",
                "reviewer_or_owner": "scientist",
                "confidence_in_outcome_context": "moderate",
                "not_model_truth_flag": "true",
            },
        ]
    ).to_csv(program_memory / "outcomes_log.csv", index=False)
    pd.DataFrame(
        [
            {
                "entity_type": "shortlist_item",
                "entity_id": "v1",
                "project_id": "proj_a",
                "workspace_id": "ws_1",
                "num_cycles_seen": 1,
                "cycle_ids_serialized": "week_1",
                "status_path_serialized": "shortlisted",
                "shortlist_count": 1,
                "carry_forward_count": 0,
                "unresolved_count": 0,
                "churn_score": 0.0,
                "latest_status": "shortlisted",
                "notes": "",
            }
        ]
    ).to_csv(program_memory / "multicycle_decision_summary.csv", index=False)

    outputs = summarize_workflow_metrics(workspace)
    cycle_df = pd.read_csv(outputs["cycle_operational_metrics.csv"])
    row = cycle_df.iloc[0]

    assert float(row["shortlist_closure_ratio"]) == 1.0
    assert float(row["open_question_resolution_ratio"]) == 1.0
    assert float(row["next_action_completion_ratio"]) == 0.5
    assert float(row["promotion_to_followup_ratio"]) == 1.0
