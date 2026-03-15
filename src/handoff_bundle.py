from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv, safe_read_json, safe_read_text
from .review_state import ensure_review_dirs
from .scope_text import brief_scope_markdown, expanded_scope_markdown


def create_handoff_bundle(
    project_dir: Path,
    bundle_id: str,
    scenario_ids: list[str],
    include_annotations: bool = True,
    include_feedback_snapshot: bool = True,
    include_scope_statement: bool = True,
) -> Path:
    paths = ensure_review_dirs(project_dir)
    bundle_root = paths.handoff_dir / bundle_id
    selected_scenarios = bundle_root / "selected_scenarios"
    selected_rankings = bundle_root / "selected_rankings"
    selected_panels = bundle_root / "selected_panels"
    selected_evidence = bundle_root / "selected_evidence"
    annotations_dir = bundle_root / "annotations"
    for directory in [bundle_root, selected_scenarios, selected_rankings, selected_panels, selected_evidence, annotations_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    manifests: list[dict[str, object]] = []
    for scenario_id in scenario_ids:
        scenario_dir = project_dir / "scenario_exports" / scenario_id
        for filename, target_dir in [
            ("scenario_summary.json", selected_scenarios),
            ("scenario_ranked_variants.csv", selected_rankings),
            ("scenario_panel.csv", selected_panels),
            ("scenario_evidence.csv", selected_evidence),
            ("scenario_notes.md", selected_scenarios),
        ]:
            source = scenario_dir / filename
            if source.exists():
                target = target_dir / f"{scenario_id}_{filename}"
                shutil.copy2(source, target)
                manifests.append({"scenario_id": scenario_id, "source_path": str(source), "bundled_path": str(target)})

    if include_feedback_snapshot and paths.feedback_log_csv.exists():
        shutil.copy2(paths.feedback_log_csv, bundle_root / "feedback_snapshot.csv")
    if include_annotations and paths.annotations_csv.exists():
        shutil.copy2(paths.annotations_csv, bundle_root / "annotations.csv")
        for note_file in paths.notes_dir.glob("*.md"):
            shutil.copy2(note_file, annotations_dir / note_file.name)
    if paths.next_actions_md.exists():
        shutil.copy2(paths.next_actions_md, bundle_root / "next_actions.md")

    project_summary = safe_read_json(project_dir / "analysis" / "analysis_snapshot.json")
    (bundle_root / "project_summary.json").write_text(json.dumps(project_summary, indent=2), encoding="utf-8")
    pd.DataFrame(manifests).to_csv(bundle_root / "bundle_manifest.csv", index=False)

    readme_lines = [
        f"# Handoff Bundle: {bundle_id}",
        "",
        f"- Project: {project_dir.name}",
        f"- Included scenarios: {', '.join(scenario_ids)}",
        "",
        "This bundle contains a reviewed subset of scenario outputs and evidence-linked artifacts for collaborator discussion.",
        "",
    ]
    if include_scope_statement:
        readme_lines.extend([brief_scope_markdown(), "", expanded_scope_markdown(), ""])
    readme_lines.extend(
        [
            "Included contents:",
            "- selected scenario summaries and ranked tables",
            "- selected panel and evidence tables when available",
            "- feedback and annotation snapshots when requested",
            "- next actions if they were recorded in the pilot workflow",
        ]
    )
    (bundle_root / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    return bundle_root
