from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv
from .workspace import WorkspaceConfig, load_workspace_config


def build_recurring_patterns(workspace: WorkspaceConfig | str | Path) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    output_dir = config.output_dir / "program_memory"
    output_dir.mkdir(parents=True, exist_ok=True)

    recurring_questions_rows: list[dict[str, object]] = []
    recurring_pattern_rows: list[dict[str, object]] = []
    question_counter: Counter[tuple[str, str]] = Counter()
    pattern_counter: Counter[tuple[str, str]] = Counter()
    projects_by_key: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    for project in config.projects:
        if not project.path.exists():
            continue
        open_questions_df = safe_read_csv(project.path / "analysis" / "open_questions.csv")
        next_actions_df = safe_read_csv(project.path / "analysis" / "next_action_table.csv")
        shortlist_df = safe_read_csv(project.path / "review" / "shortlist.csv")
        uncertainty_df = safe_read_csv(project.path / "analysis" / "priority_uncertainty_table.csv")
        feedback_df = safe_read_csv(project.path / "review" / "feedback_log.csv")

        for row in open_questions_df.to_dict(orient="records"):
            key = (str(row.get("category") or "unknown"), str(row.get("question_text") or "").strip())
            question_counter[key] += 1
            projects_by_key[key].add(project.project_id)
        for row in next_actions_df.to_dict(orient="records"):
            key = ("next_action", str(row.get("action_type") or "unknown"))
            pattern_counter[key] += 1
            projects_by_key[key].add(project.project_id)
        for row in shortlist_df.to_dict(orient="records"):
            uncertainty = str(row.get("uncertainty_level") or "").strip()
            if uncertainty:
                key = ("shortlist_uncertainty", uncertainty)
                pattern_counter[key] += 1
                projects_by_key[key].add(project.project_id)
        for row in uncertainty_df.to_dict(orient="records"):
            reason = str(row.get("uncertainty_level") or "").strip()
            if reason:
                key = ("uncertainty_level", reason)
                pattern_counter[key] += 1
                projects_by_key[key].add(project.project_id)
        for row in feedback_df.to_dict(orient="records"):
            concern = str(row.get("concern_type") or "").strip()
            if concern:
                key = ("feedback_concern", concern)
                pattern_counter[key] += 1
                projects_by_key[key].add(project.project_id)

    for (category, question_text), count in question_counter.items():
        recurring_questions_rows.append(
            {
                "category": category,
                "question_text": question_text,
                "count": count,
                "project_ids": ";".join(sorted(projects_by_key[(category, question_text)])),
            }
        )
    for (pattern_type, pattern_value), count in pattern_counter.items():
        recurring_pattern_rows.append(
            {
                "pattern_type": pattern_type,
                "pattern_value": pattern_value,
                "count": count,
                "project_ids": ";".join(sorted(projects_by_key[(pattern_type, pattern_value)])),
            }
        )

    recurring_questions_path = output_dir / "recurring_questions.csv"
    recurring_patterns_path = output_dir / "recurring_patterns.csv"
    pd.DataFrame(recurring_questions_rows).sort_values(["count", "category"], ascending=[False, True]).to_csv(recurring_questions_path, index=False)
    pd.DataFrame(recurring_pattern_rows).sort_values(["count", "pattern_type"], ascending=[False, True]).to_csv(recurring_patterns_path, index=False)

    digest_lines = ["# Pattern Digest", ""]
    if recurring_pattern_rows:
        for row in sorted(recurring_pattern_rows, key=lambda item: (-int(item["count"]), str(item["pattern_type"])))[:10]:
            digest_lines.append(f"- `{row['pattern_type']}` -> `{row['pattern_value']}` seen {row['count']} times across {row['project_ids']}.")
    else:
        digest_lines.append("- No recurring patterns were detected.")
    digest_path = output_dir / "pattern_digest.md"
    digest_path.write_text("\n".join(digest_lines), encoding="utf-8")
    return {
        "recurring_questions.csv": recurring_questions_path,
        "recurring_patterns.csv": recurring_patterns_path,
        "pattern_digest.md": digest_path,
    }
