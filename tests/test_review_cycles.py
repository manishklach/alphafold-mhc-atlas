from pathlib import Path
import json
import textwrap

import pandas as pd

from src.review_cycles import compare_review_cycles, summarize_review_cycles


def test_review_cycle_compare(tmp_path: Path) -> None:
    output_dir = tmp_path / "workspace_outputs"
    week1 = output_dir / "review_packets" / "week_1" / "review_packet_tables"
    week2 = output_dir / "review_packets" / "week_2" / "review_packet_tables"
    week1.mkdir(parents=True)
    week2.mkdir(parents=True)
    (week1.parent / "review_packet_summary.json").write_text(json.dumps({"generated_at": "2026-01-01T00:00:00+00:00", "num_projects": 1}), encoding="utf-8")
    (week2.parent / "review_packet_summary.json").write_text(json.dumps({"generated_at": "2026-01-08T00:00:00+00:00", "num_projects": 2}), encoding="utf-8")
    pd.DataFrame([{"project_id": "proj_a"}, {"project_id": "proj_b"}]).to_csv(week2 / "workspace_projects.csv", index=False)
    pd.DataFrame([{"project_id": "proj_a"}]).to_csv(week1 / "workspace_projects.csv", index=False)
    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        textwrap.dedent(
            f"""
            workspace:
              workspace_id: test_ws
              name: Test Workspace
              description: Test
              output_dir: "{output_dir.as_posix()}"
              projects:
                - id: proj_a
                  path: "{(tmp_path / 'proj_a').as_posix()}"
            """
        ),
        encoding="utf-8",
    )
    summary_outputs = summarize_review_cycles(workspace)
    compare_outputs = compare_review_cycles(workspace, "week_2", "week_1")
    summary_df = pd.read_csv(summary_outputs["cycle_summary.csv"])
    comparison_df = pd.read_csv(compare_outputs["cycle_to_cycle_comparison.csv"])
    assert "week_1" in summary_df["cycle_id"].astype(str).tolist()
    assert "new" in comparison_df["change_type"].astype(str).tolist()
