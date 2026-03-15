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
