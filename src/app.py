from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.data_access import preview_table, safe_read_csv, safe_read_json
from src.demo_loader import DEMO_ROOT, list_demo_projects, load_demo_readme, resolve_demo_project
from src.evidence_view import build_variant_evidence_bundle, export_variant_evidence_bundle
from src.annotations import add_annotation
from src.checklists import load_checklist_templates, run_checklist
from src.decision_packet import generate_workspace_decision_packet
from src.feedback import add_feedback, summarize_feedback
from src.feedback_schema import FeedbackEntry
from src.handoff_bundle import create_handoff_bundle
from src.next_actions import build_next_actions
from src.open_questions import build_open_questions
from src.pilot_workflow import build_review_analytics, initialize_pilot_workflow
from src.project_history import build_project_history
from src.project_index import build_project_inventory, load_project_report, load_project_tables, write_project_inventory
from src.review_packet import generate_workspace_review_packet
from src.review_queue import create_review_queue_from_scenario, update_review_item
from src.resource_paths import REPO_ROOT, repo_or_resource_path
from src.role_views import export_role_views
from src.scenario_analysis import (
    build_evidence_exports,
    compare_scenarios,
    export_scenario_comparison,
    export_scenario_result,
    run_scenario_analysis,
)
from src.scenario_state import ScenarioState, load_scenario_state, save_scenario_state
from src.scope_text import brief_scope_markdown, expanded_scope_markdown
from src.session_logging import log_session_action, start_session
from src.shortlist import refresh_shortlists
from src.version import __version__
from src.workspace import load_workspace_config
from src.workspace_index import build_workspace_inventory, write_workspace_inventory

OUTPUTS_ROOT = REPO_ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive local analyst app for the peptide-MHC atlas.")
    parser.add_argument("--project", help="Path to an existing project output directory.", default=None)
    parser.add_argument("--demo", help="Load a curated demo project by name.", default=None)
    parser.add_argument("--workspace", help="Path to a workspace YAML or JSON config.", default=None)
    parser.add_argument("--list-demos", action="store_true")
    parser.add_argument("--list-project-artifacts", help="Print project inventory JSON for the given project path.")
    parser.add_argument("--write-project-inventory", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list_demos:
        print("\n".join(list_demo_projects()))
        return
    if args.list_project_artifacts:
        inventory = build_project_inventory(_resolve_project_arg(args.list_project_artifacts))
        print(json.dumps(inventory, indent=2))
        return
    if _running_in_streamlit():
        render_streamlit_app(args)
        return
    launch_streamlit(args)


def launch_streamlit(args: argparse.Namespace) -> None:
    import importlib.util

    if importlib.util.find_spec("streamlit") is None:
        raise SystemExit("Streamlit is not installed. Install the app extras with `pip install .[app]`.")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).resolve()),
        "--server.address",
        args.host,
        "--server.port",
        str(args.port),
        "--",
    ]
    if args.project:
        command.extend(["--project", args.project])
    if args.demo:
        command.extend(["--demo", args.demo])
    if args.workspace:
        command.extend(["--workspace", args.workspace])
    if args.write_project_inventory:
        command.append("--write-project-inventory")
    subprocess.run(command, cwd=REPO_ROOT, check=False)


def launch_app(
    project: str | None = None,
    demo: str | None = None,
    workspace: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8501,
    write_project_inventory: bool = False,
) -> None:
    launch_streamlit(
        argparse.Namespace(
            project=project,
            demo=demo,
            workspace=workspace,
            list_demos=False,
            list_project_artifacts=None,
            write_project_inventory=write_project_inventory,
            host=host,
            port=port,
        )
    )


def render_streamlit_app(args: argparse.Namespace) -> None:
    import streamlit as st

    st.set_page_config(page_title="Peptide-MHC Atlas", layout="wide")
    st.title("Peptide-MHC Atlas Decision Support")
    st.caption(f"Version {__version__} | Local-first analyst interface")

    templates = load_scenario_templates(repo_or_resource_path("data", "scenario_templates.yaml"))
    source_options = ["Local project", "Demo project", "Workspace"]
    default_source = "Workspace" if args.workspace else ("Demo project" if args.demo else "Local project")
    source_mode = st.sidebar.radio("Source", source_options, index=source_options.index(default_source))
    workspace_config = _select_workspace_config(st, source_mode, args)
    if source_mode == "Workspace":
        if workspace_config is None:
            st.info("Select a workspace config to begin.")
            return
        render_workspace_app(st, workspace_config)
        return

    project_dir = _select_project_dir(st, source_mode, args)
    if project_dir is None:
        st.info("Select a demo or local project to begin.")
        return

    if args.write_project_inventory:
        write_project_inventory(project_dir)

    inventory = build_project_inventory(project_dir)
    tables = load_project_tables(project_dir)
    report_text = load_project_report(project_dir)

    st.sidebar.markdown("### Project")
    st.sidebar.code(str(project_dir))
    st.sidebar.caption(f"Package version: {__version__}")
    page = st.sidebar.selectbox(
        "Page",
        [
            "Project Overview",
            "Variant Explorer",
            "Ranking Explorer",
            "Panel Designer",
            "Cross-Allele Comparison",
            "Scenario Analysis",
            "Scenario Comparison",
            "Review Queue",
            "Shortlists",
            "Feedback",
            "Notes",
            "Handoff Exports",
            "Checklists",
            "Case Studies",
            "Hypotheses",
            "Reports / Exports",
        ],
    )
    session = _ensure_streamlit_session(st, project_dir)
    _log_page_view(project_dir, session["session_id"], page)

    scenario_a = _scenario_controls(st.sidebar, "Scenario A", templates, tables)
    scenario_b = _scenario_controls(st.sidebar, "Scenario B", templates, tables, key_prefix="b_")

    if page == "Project Overview":
        _render_overview(st, inventory, report_text)
    elif page == "Variant Explorer":
        _render_variant_explorer(st, tables, inventory)
    elif page == "Ranking Explorer":
        _render_ranking_explorer(st, tables, inventory)
    elif page == "Panel Designer":
        _render_panel_designer(st, tables)
    elif page == "Cross-Allele Comparison":
        _render_cross_allele(st, tables)
    elif page == "Scenario Analysis":
        _render_scenario_analysis(st, project_dir, tables, scenario_a)
    elif page == "Scenario Comparison":
        _render_scenario_comparison(st, project_dir, tables, scenario_a, scenario_b)
    elif page == "Review Queue":
        _render_review_queue(st, project_dir, tables, scenario_a, session["session_id"])
    elif page == "Shortlists":
        _render_shortlists(st, project_dir)
    elif page == "Feedback":
        _render_feedback(st, project_dir, tables, session["session_id"])
    elif page == "Notes":
        _render_notes(st, project_dir, tables, session["session_id"])
    elif page == "Handoff Exports":
        _render_handoff_exports(st, project_dir, scenario_a, session["session_id"])
    elif page == "Checklists":
        _render_checklists(st, project_dir, session["session_id"])
    elif page == "Case Studies":
        _render_case_studies(st, project_dir)
    elif page == "Hypotheses":
        _render_hypotheses(st, tables)
    elif page == "Reports / Exports":
        _render_reports(st, project_dir, report_text, inventory)


def load_scenario_templates(path: Path) -> list[ScenarioState]:
    if not path.exists():
        return []
    payload = safe_read_json(path) if path.suffix.lower() == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = payload.get("templates", []) if isinstance(payload, dict) else []
    return [ScenarioState(**template) for template in templates]


def _select_project_dir(st, source_mode: str, args: argparse.Namespace) -> Path | None:
    if source_mode == "Demo project":
        demos = list_demo_projects()
        default_demo = args.demo if args.demo in demos else (demos[0] if demos else None)
        selected_demo = st.sidebar.selectbox("Demo", demos, index=demos.index(default_demo) if default_demo else 0) if demos else None
        if not selected_demo:
            return None
        if st.sidebar.checkbox("Show demo README", value=False):
            st.sidebar.markdown(load_demo_readme(selected_demo))
        return resolve_demo_project(selected_demo)

    projects = sorted(path for path in OUTPUTS_ROOT.iterdir() if path.is_dir()) if OUTPUTS_ROOT.exists() else []
    default_path = _resolve_project_arg(args.project) if args.project else (projects[0] if projects else None)
    options = [str(path) for path in projects]
    custom_path = st.sidebar.text_input("Project path", value=str(default_path) if default_path else "")
    if custom_path:
        path = _resolve_project_arg(custom_path)
        return path if path.exists() else None
    return default_path if default_path and default_path.exists() else None


def _select_workspace_config(st, source_mode: str, args: argparse.Namespace):
    if source_mode != "Workspace":
        return None
    default_path = _resolve_project_arg(args.workspace) if args.workspace else (REPO_ROOT / "workspaces" / "demo_workspace.yaml")
    workspace_path = st.sidebar.text_input("Workspace config", value=str(default_path))
    if not workspace_path:
        return None
    path = _resolve_project_arg(workspace_path)
    return load_workspace_config(path) if path.exists() else None


def _scenario_controls(st_sidebar, title: str, templates: list[ScenarioState], tables: dict[str, pd.DataFrame], key_prefix: str = "") -> ScenarioState:
    st_sidebar.markdown(f"### {title}")
    template_options = {template.label: template for template in templates}
    labels = list(template_options)
    selected_label = st_sidebar.selectbox(
        f"{title} template",
        labels,
        key=f"{key_prefix}template",
    )
    base = template_options[selected_label]
    priority_df = tables.get("priority", pd.DataFrame())
    summary_df = tables.get("summary", pd.DataFrame())

    ranking_mode = st_sidebar.selectbox(
        f"{title} ranking mode",
        options=sorted(priority_df["ranking_mode"].dropna().unique().tolist()) if not priority_df.empty and "ranking_mode" in priority_df.columns else [base.ranking_mode],
        index=0,
        key=f"{key_prefix}ranking_mode",
    )
    alleles = st_sidebar.multiselect(
        f"{title} alleles",
        options=sorted(summary_df["allele_name"].dropna().unique().tolist()) if not summary_df.empty and "allele_name" in summary_df.columns else [],
        default=base.alleles,
        key=f"{key_prefix}alleles",
    )
    positions = st_sidebar.multiselect(
        f"{title} positions",
        options=sorted(pd.to_numeric(summary_df["mutated_position"], errors="coerce").dropna().astype(int).unique().tolist()) if not summary_df.empty and "mutated_position" in summary_df.columns else [],
        default=base.mutation_positions,
        key=f"{key_prefix}positions",
    )
    substitutions = st_sidebar.multiselect(
        f"{title} substitutions",
        options=sorted(summary_df["mut_residue"].dropna().astype(str).unique().tolist()) if not summary_df.empty and "mut_residue" in summary_df.columns else [],
        default=base.substitutions,
        key=f"{key_prefix}substitutions",
    )
    evidence_threshold = st_sidebar.slider(
        f"{title} evidence coverage",
        min_value=0.0,
        max_value=1.0,
        value=float(base.evidence_coverage_threshold),
        step=0.05,
        key=f"{key_prefix}coverage",
    )
    uncertainty = st_sidebar.multiselect(
        f"{title} uncertainty",
        options=["low", "moderate", "high", "insufficient_data"],
        default=base.allowed_uncertainty,
        key=f"{key_prefix}uncertainty",
    )
    require_structural = st_sidebar.checkbox(
        f"{title} require structural support",
        value=base.require_structural_support,
        key=f"{key_prefix}structural",
    )
    anchor_only = st_sidebar.checkbox(
        f"{title} anchor-only",
        value=base.anchor_only,
        key=f"{key_prefix}anchor_only",
    )
    panel_size = st_sidebar.number_input(
        f"{title} panel size",
        min_value=1,
        max_value=50,
        value=int(base.panel_size or 10),
        key=f"{key_prefix}panel_size",
    )
    return ScenarioState(
        scenario_id=f"{key_prefix or 'a'}{base.scenario_id}",
        label=base.label,
        ranking_mode=ranking_mode,
        alleles=alleles,
        peptides=base.peptides,
        mutation_positions=positions,
        substitutions=substitutions,
        evidence_coverage_threshold=evidence_threshold,
        allowed_uncertainty=uncertainty,
        require_structural_support=require_structural,
        anchor_only=anchor_only,
        case_study_id=base.case_study_id,
        panel_size=panel_size,
        notes=base.notes,
    )


def _render_overview(st, inventory: dict[str, object], report_text: str) -> None:
    coverage = inventory["coverage"]
    st.info("This app operates on existing local outputs. Rankings and panels remain drillable to file-backed evidence.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alleles", coverage["num_alleles"])
    c2.metric("Variants", coverage["num_variants"])
    c3.metric("Priority rows", coverage["prioritization_rows"])
    c4.metric("Panel rows", coverage["panel_rows"])
    st.subheader("Available modules")
    st.write(", ".join(inventory["available_modules"]))
    if inventory["notes"]:
        st.warning(" | ".join(inventory["notes"]))
    with st.expander("Conservative by design", expanded=True):
        st.markdown(brief_scope_markdown())
        st.markdown(expanded_scope_markdown())
    st.subheader("Report")
    st.text(report_text or "No report.md was available.")


def _render_variant_explorer(st, tables: dict[str, pd.DataFrame], inventory: dict[str, object]) -> None:
    summary_df = tables.get("summary", pd.DataFrame())
    st.subheader("Variant summary")
    st.dataframe(preview_table(summary_df, 200), use_container_width=True)
    if summary_df.empty or "variant_id" not in summary_df.columns:
        st.info("Variant-level summary data are not available.")
        return
    variant_id = st.selectbox("Variant", summary_df["variant_id"].astype(str).tolist())
    bundle = build_variant_evidence_bundle(variant_id, tables)
    st.subheader("Evidence drilldown")
    st.json(bundle)


def _render_ranking_explorer(st, tables: dict[str, pd.DataFrame], inventory: dict[str, object]) -> None:
    priority_df = tables.get("priority", pd.DataFrame())
    if priority_df.empty:
        st.info("No prioritization output was found.")
        return
    mode = st.selectbox("Ranking mode", sorted(priority_df["ranking_mode"].dropna().unique().tolist()))
    subset = priority_df[priority_df["ranking_mode"] == mode].reset_index(drop=True)
    st.dataframe(preview_table(subset, 200), use_container_width=True)
    if not subset.empty:
        variant_id = st.selectbox("Inspect ranked variant", subset["variant_id"].astype(str).tolist(), key="rank_variant")
        st.json(build_variant_evidence_bundle(variant_id, tables))


def _render_panel_designer(st, tables: dict[str, pd.DataFrame]) -> None:
    panel_df = tables.get("panel", pd.DataFrame())
    coverage_df = tables.get("panel_coverage", pd.DataFrame())
    if panel_df.empty:
        st.info("No panel-design output was found.")
        return
    st.subheader("Selected panel rows")
    st.dataframe(preview_table(panel_df, 200), use_container_width=True)
    st.subheader("Coverage summary")
    st.dataframe(coverage_df, use_container_width=True)


def _render_cross_allele(st, tables: dict[str, pd.DataFrame]) -> None:
    cross_df = tables.get("cross_allele_summary", pd.DataFrame())
    allele_df = tables.get("allele_tolerance", pd.DataFrame())
    pocket_df = tables.get("pocket_signature", pd.DataFrame())
    if cross_df.empty and allele_df.empty and pocket_df.empty:
        st.info("Cross-allele outputs are not available for this project.")
        return
    st.subheader("Cross-allele summary")
    st.dataframe(cross_df, use_container_width=True)
    st.subheader("Allele tolerance")
    st.dataframe(allele_df, use_container_width=True)
    st.subheader("Pocket signatures")
    st.dataframe(preview_table(pocket_df, 100), use_container_width=True)


def _render_scenario_analysis(st, project_dir: Path, tables: dict[str, pd.DataFrame], scenario: ScenarioState) -> None:
    st.subheader("Scenario configuration")
    st.json(scenario.to_dict())
    result = run_scenario_analysis(scenario, tables)
    st.subheader("Scenario summary")
    st.json(result["summary"])
    st.subheader("Ranked variants")
    st.dataframe(preview_table(result["ranked_variants"], 200), use_container_width=True)
    st.subheader("Scenario panel")
    st.dataframe(preview_table(result["panel"], 200), use_container_width=True)
    if st.button("Export scenario", key="export_scenario_a"):
        export_dir = project_dir / "scenario_exports" / scenario.scenario_id
        export_scenario_result(result, export_dir)
        build_evidence_exports(result, tables, export_dir)
        st.success(f"Scenario exported to {export_dir}")
    if st.button("Save scenario JSON", key="save_scenario_a"):
        save_dir = project_dir / "saved_scenarios"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_scenario_state(scenario, save_dir / f"{scenario.scenario_id}.json")
        st.success(f"Saved scenario to {save_path}")


def _render_review_queue(st, project_dir: Path, tables: dict[str, pd.DataFrame], scenario: ScenarioState, session_id: str) -> None:
    st.subheader("Review queue")
    scenario_result = run_scenario_analysis(scenario, tables)
    review_path = project_dir / "review" / "review_queue.csv"
    if st.button("Initialize pilot workflow"):
        initialize_pilot_workflow(project_dir, scenario.scenario_id)
        log_session_action(project_dir, session_id, "pilot_workflow_initialized", {"scenario_id": scenario.scenario_id})
        st.success("Pilot workflow initialized.")
    if st.button("Generate review queue from scenario"):
        create_review_queue_from_scenario(project_dir, scenario_result)
        log_session_action(project_dir, session_id, "review_queue_generated", {"scenario_id": scenario.scenario_id})
        st.success(f"Wrote {review_path}")
    queue_df = safe_read_csv(review_path)
    if queue_df.empty:
        st.info("No review queue exists yet. Generate one from the current scenario.")
        return
    st.dataframe(preview_table(queue_df, 200), use_container_width=True)
    entity_id = st.selectbox("Review item", queue_df["entity_id"].astype(str).tolist())
    status = st.selectbox(
        "Status",
        ["queued", "shortlisted", "rejected", "uncertain", "request_more_evidence", "experimental_followup", "report_inclusion", "discussion"],
    )
    rationale = st.text_area("Rationale", key="review_rationale")
    next_action = st.text_input("Next action", key="review_next_action")
    tags = st.text_input("Tags (; separated)", key="review_tags")
    if st.button("Update review item"):
        update_review_item(
            project_dir,
            entity_id,
            review_status=status,
            rationale=rationale,
            next_action=next_action,
            tags=[tag.strip() for tag in tags.split(";") if tag.strip()],
        )
        log_session_action(project_dir, session_id, "review_item_updated", {"entity_id": entity_id, "status": status})
        st.success("Review item updated.")
    st.subheader("Evidence drilldown")
    st.json(build_variant_evidence_bundle(entity_id, load_project_tables(project_dir)))


def _render_shortlists(st, project_dir: Path) -> None:
    shortlist_path = project_dir / "review" / "shortlist.csv"
    if st.button("Refresh shortlists from review queue"):
        refresh_shortlists(project_dir)
        st.success(f"Updated {shortlist_path}")
    shortlist_df = safe_read_csv(shortlist_path)
    rejected_df = safe_read_csv(project_dir / "review" / "rejected_items.csv")
    if shortlist_df.empty:
        st.info("No shortlist is available yet.")
    else:
        st.subheader("Shortlist")
        st.dataframe(preview_table(shortlist_df, 200), use_container_width=True)
    if not rejected_df.empty:
        st.subheader("Rejected items")
        st.dataframe(preview_table(rejected_df, 100), use_container_width=True)


def _render_feedback(st, project_dir: Path, tables: dict[str, pd.DataFrame], session_id: str) -> None:
    st.subheader("Structured feedback")
    summary_df = tables.get("summary", pd.DataFrame())
    queue_df = safe_read_csv(project_dir / "review" / "review_queue.csv")
    entity_options = []
    if not queue_df.empty and "entity_id" in queue_df.columns:
        entity_options.extend(queue_df["entity_id"].astype(str).tolist())
    if not summary_df.empty and "variant_id" in summary_df.columns:
        entity_options.extend([item for item in summary_df["variant_id"].astype(str).tolist() if item not in entity_options])
    entity_id = st.selectbox("Entity", entity_options if entity_options else [""])
    entity_type = st.selectbox("Entity type", ["variant", "scenario", "panel", "hypothesis", "report", "case_study"])
    reviewer_name = st.text_input("Reviewer name", value="pilot_user")
    reviewer_role = st.text_input("Reviewer role", value="collaborator")
    sentiment = st.selectbox("Sentiment", ["positive", "neutral", "negative", "mixed"])
    usefulness = st.slider("Usefulness rating", 1, 5, 3)
    clarity = st.slider("Clarity rating", 1, 5, 3)
    confidence = st.selectbox("Confidence in output", ["low", "moderate", "high"])
    concern = st.selectbox(
        "Concern type",
        [
            "insufficient_evidence",
            "unclear_ranking",
            "biological_caveat",
            "missing_context",
            "scenario_needs_adjustment",
            "panel_needs_diversity_change",
            "export_needs_improvement",
            "ui_confusing",
            "data_quality_issue",
            "other",
        ],
    )
    comment = st.text_area("Comment")
    followup = st.text_input("Requested follow-up")
    status = st.selectbox("Feedback status", ["open", "reviewed", "resolved"])
    if st.button("Submit feedback"):
        add_feedback(
            project_dir,
            FeedbackEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                sentiment=sentiment,
                usefulness_rating=usefulness,
                clarity_rating=clarity,
                confidence_in_output=confidence,
                concern_type=concern,
                free_text_comment=comment,
                requested_followup=followup,
                status=status,
            ),
        )
        summarize_feedback(project_dir)
        build_review_analytics(project_dir)
        log_session_action(project_dir, session_id, "feedback_submitted", {"entity_id": entity_id, "concern_type": concern})
        st.success("Feedback saved.")
    feedback_df = safe_read_csv(project_dir / "review" / "feedback_log.csv")
    st.dataframe(preview_table(feedback_df, 200), use_container_width=True)


def _render_notes(st, project_dir: Path, tables: dict[str, pd.DataFrame], session_id: str) -> None:
    st.subheader("Annotations and notes")
    summary_df = tables.get("summary", pd.DataFrame())
    entity_options = summary_df["variant_id"].astype(str).tolist() if not summary_df.empty and "variant_id" in summary_df.columns else [""]
    entity_id = st.selectbox("Entity", entity_options)
    entity_type = st.selectbox("Entity type", ["variant", "scenario", "panel", "hypothesis", "cross_allele"], key="notes_entity_type")
    tags = st.text_input("Tags (; separated)", key="note_tags")
    category = st.selectbox("Category", ["general", "biological_caveat", "followup", "discussion"])
    note_text = st.text_area("Note", key="note_text")
    if st.button("Save note"):
        add_annotation(
            project_dir,
            entity_type=entity_type,
            entity_id=entity_id,
            note_text=note_text,
            tags=[tag.strip() for tag in tags.split(";") if tag.strip()],
            category=category,
        )
        log_session_action(project_dir, session_id, "annotation_saved", {"entity_id": entity_id, "category": category})
        st.success("Note saved.")
    annotations_df = safe_read_csv(project_dir / "review" / "annotations.csv")
    st.dataframe(preview_table(annotations_df, 200), use_container_width=True)


def _render_handoff_exports(st, project_dir: Path, scenario: ScenarioState, session_id: str) -> None:
    st.subheader("Handoff bundles")
    bundle_id = st.text_input("Bundle ID", value=f"handoff_{scenario.scenario_id}")
    scenario_ids = st.text_input("Scenario IDs (; separated)", value=scenario.scenario_id)
    if st.button("Create handoff bundle"):
        bundle_root = create_handoff_bundle(
            project_dir,
            bundle_id=bundle_id,
            scenario_ids=[item.strip() for item in scenario_ids.split(";") if item.strip()],
        )
        log_session_action(project_dir, session_id, "handoff_bundle_created", {"bundle_id": bundle_id})
        st.success(f"Created {bundle_root}")
    handoff_root = project_dir / "handoff_bundles"
    if handoff_root.exists():
        bundles = sorted(path.name for path in handoff_root.iterdir() if path.is_dir())
        st.write(bundles)


def _render_checklists(st, project_dir: Path, session_id: str) -> None:
    st.subheader("Review checklists")
    templates = load_checklist_templates().get("templates", [])
    labels = [item.get("template_id", "") for item in templates]
    if not labels:
        st.info("No checklist templates are available.")
        return
    template_id = st.selectbox("Checklist template", labels)
    if st.button("Run checklist"):
        path = run_checklist(project_dir, template_id)
        log_session_action(project_dir, session_id, "checklist_run", {"template_id": template_id})
        st.success(f"Wrote {path}")
    runs_df = safe_read_csv(project_dir / "review" / "checklists" / "checklist_runs.csv")
    st.dataframe(preview_table(runs_df, 200), use_container_width=True)


def _render_scenario_comparison(st, project_dir: Path, tables: dict[str, pd.DataFrame], scenario_a: ScenarioState, scenario_b: ScenarioState) -> None:
    result_a = run_scenario_analysis(scenario_a, tables)
    result_b = run_scenario_analysis(scenario_b, tables)
    comparison = compare_scenarios(result_a, result_b)
    st.subheader("Scenario A")
    st.json(result_a["summary"])
    st.subheader("Scenario B")
    st.json(result_b["summary"])
    st.subheader("Comparison")
    st.dataframe(comparison["comparison"], use_container_width=True)
    st.subheader("Rank diff")
    st.dataframe(preview_table(comparison["rank_diff"], 200), use_container_width=True)
    st.subheader("Panel diff")
    st.dataframe(preview_table(comparison["panel_diff"], 200), use_container_width=True)
    st.text(comparison["summary_markdown"])
    if st.button("Export scenario comparison"):
        export_dir = project_dir / "scenario_exports" / f"{scenario_a.scenario_id}_vs_{scenario_b.scenario_id}"
        export_scenario_comparison(comparison, export_dir)
        st.success(f"Comparison exported to {export_dir}")


def _render_case_studies(st, project_dir: Path) -> None:
    case_root = project_dir / "case_studies"
    if not case_root.exists():
        st.info("No case-study outputs were found.")
        return
    case_dirs = sorted(path for path in case_root.iterdir() if path.is_dir())
    if not case_dirs:
        st.info("No case-study directories were found.")
        return
    selected = st.selectbox("Case study", [path.name for path in case_dirs])
    case_dir = case_root / selected
    st.json(safe_read_json(case_dir / "summary.json"))
    for path in sorted(case_dir.glob("*.csv")):
        st.markdown(f"**{path.name}**")
        st.dataframe(preview_table(pd.read_csv(path), 100), use_container_width=True)


def _render_hypotheses(st, tables: dict[str, pd.DataFrame]) -> None:
    hypotheses_df = tables.get("hypotheses", pd.DataFrame())
    if hypotheses_df.empty:
        st.info("No hypotheses table was found.")
        return
    st.dataframe(preview_table(hypotheses_df, 200), use_container_width=True)


def _render_reports(st, project_dir: Path, report_text: str, inventory: dict[str, object]) -> None:
    st.subheader("Report")
    st.text(report_text or "No report.md was available.")
    st.subheader("Scope and limitations")
    st.markdown(brief_scope_markdown())
    st.markdown(expanded_scope_markdown())
    st.subheader("Project inventory")
    st.json(inventory)
    if st.button("Write project inventory file"):
        path = write_project_inventory(project_dir)
        st.success(f"Wrote {path}")


def render_workspace_app(st, workspace_config) -> None:
    inventory = build_workspace_inventory(workspace_config)
    st.sidebar.markdown("### Workspace")
    st.sidebar.code(str(workspace_config.source_path))
    page = st.sidebar.selectbox(
        "Workspace page",
        [
            "Workspace Overview",
            "Project Portfolio",
            "Changes Since Last Review",
            "Weekly Review Packet",
            "Role Views",
            "Open Questions",
            "Next Actions",
            "Project History",
            "Review Queues / Shortlists",
            "Handoff Bundles",
        ],
    )
    projects_df = pd.DataFrame(inventory["projects"])
    selected_project_id = st.sidebar.selectbox("Project", projects_df["project_id"].tolist() if not projects_df.empty else [""])
    selected_project_path = None
    if not projects_df.empty and selected_project_id:
        selected_row = projects_df[projects_df["project_id"] == selected_project_id].iloc[0].to_dict()
        selected_project_path = Path(selected_row["project_path"])
    if page == "Workspace Overview":
        st.subheader(workspace_config.name)
        st.write(workspace_config.description)
        st.dataframe(pd.DataFrame(inventory["summary"]), use_container_width=True)
        st.markdown(brief_scope_markdown())
    elif page == "Project Portfolio":
        st.dataframe(projects_df, use_container_width=True)
    elif page == "Changes Since Last Review" and selected_project_path is not None:
        build_project_history(selected_project_path)
        st.text((selected_project_path / "history" / "change_summary.md").read_text(encoding="utf-8"))
    elif page == "Weekly Review Packet":
        if st.button("Generate workspace review packet"):
            packet_dir = generate_workspace_review_packet(workspace_config)
            st.success(f"Wrote {packet_dir}")
        packet_root = workspace_config.output_dir / "review_packets"
        if packet_root.exists():
            st.write(sorted(path.name for path in packet_root.iterdir() if path.is_dir()))
    elif page == "Role Views" and selected_project_path is not None:
        paths = export_role_views(selected_project_path)
        role = st.selectbox("Role", ["scientist", "comp_lead", "manager"])
        st.text(paths[role].read_text(encoding="utf-8"))
    elif page == "Open Questions" and selected_project_path is not None:
        build_open_questions(selected_project_path)
        st.dataframe(preview_table(safe_read_csv(selected_project_path / "analysis" / "open_questions.csv"), 200), use_container_width=True)
    elif page == "Next Actions" and selected_project_path is not None:
        build_next_actions(selected_project_path)
        st.dataframe(preview_table(safe_read_csv(selected_project_path / "analysis" / "next_action_table.csv"), 200), use_container_width=True)
    elif page == "Project History" and selected_project_path is not None:
        build_project_history(selected_project_path)
        st.json(safe_read_json(selected_project_path / "history" / "project_history.json"))
    elif page == "Review Queues / Shortlists" and selected_project_path is not None:
        st.subheader("Review queue")
        st.dataframe(preview_table(safe_read_csv(selected_project_path / "review" / "review_queue.csv"), 200), use_container_width=True)
        st.subheader("Shortlist")
        st.dataframe(preview_table(safe_read_csv(selected_project_path / "review" / "shortlist.csv"), 200), use_container_width=True)
    elif page == "Handoff Bundles" and selected_project_path is not None:
        handoff_root = selected_project_path / "handoff_bundles"
        st.write(sorted(path.name for path in handoff_root.iterdir() if path.is_dir()) if handoff_root.exists() else [])
    else:
        st.info("This workspace page needs a valid selected project or generated packet.")


def _resolve_project_arg(value: str | None) -> Path:
    if not value:
        return OUTPUTS_ROOT
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _ensure_streamlit_session(st, project_dir: Path) -> dict[str, object]:
    current_project = str(project_dir.resolve())
    active = st.session_state.get("pilot_session")
    if not active or active.get("project_dir") != current_project:
        session = start_session(project_dir, reviewer="streamlit_user")
        active = {"project_dir": current_project, **session}
        st.session_state["pilot_session"] = active
    return active


def _log_page_view(project_dir: Path, session_id: str, page: str) -> None:
    marker = f"page::{page}"
    if marker == getattr(_log_page_view, "_last_marker", None):
        return
    _log_page_view._last_marker = marker
    log_session_action(project_dir, session_id, "page_viewed", {"page": page})


if __name__ == "__main__":
    main()
