from pathlib import Path
import textwrap

import pandas as pd

from src.rationale_tracking import build_rationale_tracking


def test_rationale_tracking_detects_changes(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "review").mkdir(parents=True)
    week1 = project / "review_packets" / "week_1" / "review_packet_tables"
    week1.mkdir(parents=True)

    pd.DataFrame([{"entity_id": "v1", "review_status": "shortlisted", "rationale": "stronger evidence"}]).to_csv(
        week1 / "shortlist.csv", index=False
    )
    pd.DataFrame([{"entity_id": "v1", "review_status": "shortlisted", "rationale": "external feedback"}]).to_csv(
        project / "review" / "shortlist.csv", index=False
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

    outputs = build_rationale_tracking(workspace)
    lineage_df = pd.read_csv(outputs["rationale_lineage.csv"])
    changes_df = pd.read_csv(outputs["rationale_change_log.csv"])

    assert "v1" in lineage_df["entity_id"].astype(str).tolist()
    assert not changes_df.empty
    assert bool(changes_df.iloc[0]["changed_from_prior_flag"])


def test_rationale_tracking_uses_entity_specific_prior_cycle(tmp_path: Path) -> None:
    project = tmp_path / "project_a"
    (project / "review").mkdir(parents=True)
    week1 = project / "review_packets" / "week_1" / "review_packet_tables"
    week2 = project / "review_packets" / "week_2" / "review_packet_tables"
    week1.mkdir(parents=True)
    week2.mkdir(parents=True)

    pd.DataFrame([{"entity_id": "v1", "review_status": "shortlisted", "rationale": "week1 rationale"}]).to_csv(
        week1 / "shortlist.csv", index=False
    )
    pd.DataFrame([{"entity_id": "v2", "review_status": "shortlisted", "rationale": "week2 rationale"}]).to_csv(
        week2 / "shortlist.csv", index=False
    )
    pd.DataFrame([{"entity_id": "v1", "review_status": "shortlisted", "rationale": "current rationale"}]).to_csv(
        project / "review" / "shortlist.csv", index=False
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

    outputs = build_rationale_tracking(workspace)
    lineage_df = pd.read_csv(outputs["rationale_lineage.csv"])
    current_v1 = lineage_df[(lineage_df["entity_id"] == "v1") & (lineage_df["cycle_id"] == "current")].iloc[0]

    assert current_v1["prior_cycle_id"] == "week_1"
