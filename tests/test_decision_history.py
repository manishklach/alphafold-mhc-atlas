from pathlib import Path
import textwrap

import pandas as pd

from src.decision_history import build_decision_history


def test_build_decision_history_tracks_carry_forward_and_resolved(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "analysis").mkdir(parents=True)
    (project / "review").mkdir(parents=True)
    packet_tables = project / "review_packets" / "week_1" / "review_packet_tables"
    packet_tables.mkdir(parents=True)
    history_dir = project / "history"
    history_dir.mkdir(parents=True)

    (project / "analysis" / "summary.csv").write_text("variant_id,score\nv1,1\n", encoding="utf-8")
    (project / "analysis" / "project_inventory.json").write_text("{}", encoding="utf-8")
    (project / "analysis" / "analysis_snapshot.json").write_text("{}", encoding="utf-8")
    (project / "analysis" / "report_summary.json").write_text("{}", encoding="utf-8")
    (project / "analysis" / "priority_uncertainty_table.csv").write_text(
        "variant_id,ranking_mode,uncertainty_level,uncertainty_reasons_serialized\nv1,disruptive_mutations,high,missing_support\n",
        encoding="utf-8",
    )
    (project / "analysis" / "ranking_stability.csv").write_text(
        "ranking_mode,variant_id,rank_shift,stability_notes\n, ,,\n",
        encoding="utf-8",
    )
    (project / "analysis" / "next_action_table.csv").write_text(
        "entity_type,entity_id,action_type,priority_level,rationale,supporting_artifacts,owner_role_suggestion,status\nvariant,v1,review_in_meeting,high,Discuss,current,manager,open\n",
        encoding="utf-8",
    )
    (project / "review" / "shortlist.csv").write_text(
        "entity_id,review_status,rationale,uncertainty_level\nv1,shortlisted,carry forward,high\n",
        encoding="utf-8",
    )
    (packet_tables / "shortlist.csv").write_text(
        "entity_id,review_status,rationale\nv1,shortlisted,earlier shortlist\n",
        encoding="utf-8",
    )
    (packet_tables / "open_questions.csv").write_text(
        "question_id,category,question_text\nq_old,insufficient_evidence,Old question\n",
        encoding="utf-8",
    )
    (packet_tables / "next_action_table.csv").write_text(
        "entity_type,entity_id,action_type,priority_level,rationale,supporting_artifacts,owner_role_suggestion,status\nvariant,v1,review_in_meeting,high,Earlier,current,manager,open\n",
        encoding="utf-8",
    )
    (project / "review_packets" / "week_1" / "review_packet_summary.json").write_text(
        '{"generated_at":"2026-01-01T00:00:00+00:00"}',
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

    outputs = build_decision_history(workspace)
    lineage_df = pd.read_csv(outputs["decision_lineage.csv"])
    carried_df = pd.read_csv(outputs["carried_forward_items.csv"])
    resolved_df = pd.read_csv(outputs["resolved_questions.csv"])
    unresolved_df = pd.read_csv(outputs["unresolved_questions.csv"])

    assert "v1" in lineage_df["entity_id"].astype(str).tolist()
    assert "v1" in carried_df["entity_id"].astype(str).tolist()
    assert "q_old" in resolved_df["entity_id"].astype(str).tolist()
    assert not unresolved_df.empty
