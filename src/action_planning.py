from __future__ import annotations

from pathlib import Path

from .next_actions import build_next_actions
from .open_questions import build_open_questions


def build_action_plan(project_dir: Path) -> Path:
    next_actions_path = build_next_actions(project_dir)
    open_questions_path = build_open_questions(project_dir)
    output_path = project_dir / "analysis" / "action_plan.md"
    output_path.write_text(
        "\n".join(
            [
                "# Action Plan",
                "",
                f"- Next actions table: {next_actions_path.name}",
                f"- Open questions table: {open_questions_path.name}",
                "- These actions are derived from current artifacts and should be reviewed by the team before execution.",
            ]
        ),
        encoding="utf-8",
    )
    return output_path
