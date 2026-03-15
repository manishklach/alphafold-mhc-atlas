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
