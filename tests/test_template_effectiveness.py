from pathlib import Path
import json
import textwrap

import pandas as pd

from src.template_effectiveness import summarize_template_effectiveness


def test_template_effectiveness_summarizes_cycles(tmp_path: Path) -> None:
    output_dir = tmp_path / "workspace_outputs"
    for cycle_id, template_name, open_count, next_count in [
        ("week_1", "weekly_mutation_review", 2, 4),
        ("week_2", "weekly_mutation_review", 1, 4),
    ]:
        packet_dir = output_dir / "review_packets" / cycle_id
        tables_dir = packet_dir / "review_packet_tables"
        tables_dir.mkdir(parents=True)
        (packet_dir / "review_packet_summary.json").write_text(
            json.dumps(
                {
                    "workflow_template": template_name,
                    "num_projects": 1,
                    "num_open_questions": open_count,
                    "num_next_actions": next_count,
                    "num_shortlist_items": 2,
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

    outputs = summarize_template_effectiveness(workspace)
    summary_df = pd.read_csv(outputs["template_effectiveness_summary.csv"])

    assert "weekly_mutation_review" in summary_df["template_name"].astype(str).tolist()
    assert float(summary_df.iloc[0]["avg_unresolved_carryforward"]) >= 0.0
