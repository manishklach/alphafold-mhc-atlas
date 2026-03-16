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
from src.demo_loader import DEMO_ROOT, describe_demo, list_demo_projects, load_demo_readme, load_demo_walkthrough, resolve_demo_project, resolve_demo_workspace
from src.evidence_view import build_variant_evidence_bundle, export_variant_evidence_bundle
from src.annotations import add_annotation
from src.checklists import load_checklist_templates, run_checklist
from src.decision_packet import generate_workspace_decision_packet
from src.decision_history import build_decision_history
from src.feedback import add_feedback, summarize_feedback
from src.feedback_schema import FeedbackEntry
from src.handoff_bundle import create_handoff_bundle
from src.multicycle_history import summarize_multicycle_history
from src.next_actions import build_next_actions
from src.open_questions import build_open_questions
from src.outcomes import summarize_outcomes
from src.pilot_workflow import build_review_analytics, initialize_pilot_workflow
from src.program_memory import build_program_memory
from src.project_history import build_project_history
from src.project_index import build_project_inventory, load_project_report, load_project_tables, write_project_inventory
from src.rationale_tracking import build_rationale_tracking
from src.review_packet import generate_workspace_review_packet
from src.review_queue import create_review_queue_from_scenario, update_review_item
from src.review_cycles import compare_review_cycles, summarize_review_cycles
from src.resource_paths import REPO_ROOT, repo_or_resource_path
from src.recurring_patterns import build_recurring_patterns
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
from src.template_effectiveness import summarize_template_effectiveness
from src.version import __version__
from src.workflow_metrics import summarize_workflow_metrics
from src.workspace import load_workspace_config
from src.workspace_index import build_workspace_inventory, write_workspace_inventory
from src.workflow_templates import load_workflow_templates

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

    if args.demo and not args.workspace:
        metadata = describe_demo(args.demo)
        if metadata.get("has_workspace") and not metadata.get("has_project"):
            args.workspace = str(resolve_demo_workspace(args.demo))
            args.demo = None

    st.set_page_config(page_title="Peptide-MHC Atlas", layout="wide")
    st.title("Peptide-MHC Atlas Decision Support")
    st.caption(f"Version {__version__} | Local-first decision platform for structure-guided experimental prioritization")

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
        if st.sidebar.checkbox("Show demo guide", value=False):
            st.sidebar.markdown(load_demo_readme(selected_demo))
            walkthrough = load_demo_walkthrough(selected_demo)
            if walkthrough:
                st.sidebar.markdown("### Walkthrough")
                st.sidebar.markdown(walkthrough)
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
    st.info("This app operates on existing local outputs. Rankings, packets, and next actions remain drillable to file-backed evidence.")
    st.subheader("Start Here")
    st.markdown(
        "\n".join(
            [
                "- Use this product to review ranked variants, panels, and evidence before a team decision meeting.",
                "- Recommended flow: `Project Overview` -> `Ranking Explorer` -> `Review Queue` -> `Shortlists` -> `Reports / Exports`.",
                "- Best first demo: `mhc-atlas app --workspace workspaces/demo_workspace.yaml`.",
                "- Starting a real study: read `docs/NEW_RESEARCHER_GUIDE.md` and copy `examples/researcher_project_template.yaml`.",
            ]
        )
    )
    c0, c1 = st.columns(2)
    c0.markdown(
        "\n".join(
            [
                "### Who This Is For",
                "- small biotech discovery teams",
                "- translational immunology and computational biology groups",
                "- scientist-manager review workflows that need clearer decision memory",
            ]
        )
    )
    c1.markdown(
        "\n".join(
            [
                "### What Problem It Solves",
                "- replaces scattered notebooks, screenshots, and ad hoc slide conclusions",
                "- keeps prioritization and review queues linked to visible evidence",
                "- makes weekly decision review packets reproducible and caveat-aware",
            ]
        )
    )
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
    
    # Workflow-oriented grouping
    workflow_stages = {
        "1. Preparation": [
            "Workspace Overview",
            "Project Portfolio",
            "Pilot Readiness",
            "Setup Pack",
            "Role Workflow Packs",
            "Evaluation Pack",
            "Workspace Evaluation",
        ],
        "2. Analysis": [
            "Variant Explorer",
            "Cross-Allele Comparison",
            "Open Questions",
            "Scenario Analysis",
            "Hypotheses",
        ],
        "3. Review Meeting": [
            "Weekly Review Packet",
            "Review Queues / Shortlists",
            "Decision Lineage",
            "Multi-Cycle History",
            "Decision Packets",
            "Changes Since Last Review",
        ],
        "4. Execution": [
            "Execution Plans",
            "Execution Tasks",
            "Handoff Bundles",
            "Action-to-Outcome Trace",
            "Execution Metrics",
        ],
        "5. Program Learning": [
            "Outcomes",
            "Retrospective Reports",
            "Pattern Synthesis Digest",
            "Rationale Lineage",
            "Template Effectiveness",
            "Workflow Metrics",
            "Review Cycles",
            "Recurring Questions",
        ],
        "6. Calibration": [
            "External Benchmarking",
        ],
        "7. Playbooks & Robustness": [
            "Scenario Playbooks",
            "Sensitivity Testing",
            "Robustness Summary",
            "Playbook Comparison",
        ],
        "8. Collaborative Consensus": [
            "Reviewer Judgments",
            "Consensus Summary",
            "Human Robustness",
            "Combined Robustness",
        ],
        "Admin": [
            "Workflow Templates",
            "Project History",
        ]
    }

    # Flatten for the selectbox but keep the visual structure if possible
    all_pages = []
    for stage, pages in workflow_stages.items():
        all_pages.append(f"--- {stage} ---")
        all_pages.extend(pages)

    selected_index = 1 # Default to Workspace Overview
    page = st.sidebar.selectbox("Workflow Stage", all_pages, index=selected_index)
    
    if page.startswith("---"):
        st.info("Select a specific page within the workflow group.")
        return

    projects_df = pd.DataFrame(inventory["projects"])
    selected_project_id = st.sidebar.selectbox("Project", projects_df["project_id"].tolist() if not projects_df.empty else [""])
    selected_project_path = None
    if not projects_df.empty and selected_project_id:
        selected_row = projects_df[projects_df["project_id"] == selected_project_id].iloc[0].to_dict()
        selected_project_path = Path(selected_row["project_path"])

    # --- Header Explainers based on Stage ---
    if page in workflow_stages["1. Preparation"]:
        st.info("### Stage 1: Preparation\nSet up your workspace, verify pilot readiness, and export role-specific guides for your team.")
    elif page in workflow_stages["2. Analysis"]:
        st.info("### Stage 2: Analysis\nExplore structural deltas, contact changes, and allele signatures to generate follow-up hypotheses.")
    elif page in workflow_stages["3. Review Meeting"]:
        st.info("### Stage 3: Review Meeting\nUse evidence-linked packets to drive team decisions. Track how decisions evolve cycle-over-cycle.")
    elif page in workflow_stages["4. Execution"]:
        st.info("### Stage 4: Execution\nConvert decisions into actionable plans. Track task status, ownership, and traceability to outcomes.")
    elif page in workflow_stages["5. Program Learning"]:
        st.info("### Stage 5: Program Learning\nSynthesize patterns from review history and outcomes. Identify bottlenecks and refine your workflow.")
    elif page in workflow_stages["6. Calibration"]:
        st.info("### Stage 6: Calibration\nCompare your internal structural hypotheses against external ground-truth datasets.")
    elif page in workflow_stages["7. Playbooks & Robustness"]:
        st.info("### Stage 7: Playbooks & Robustness\nTest how stable your decisions are under different analytical assumptions. Use Playbooks to reuse proven prioritization frames.")
    elif page in workflow_stages["8. Collaborative Consensus"]:
        st.info("### Stage 8: Collaborative Consensus\nCompare independent human judgments against analytical evidence. Identify items with strong consensus vs. items requiring active discussion.")

    if page == "Workspace Overview":
        st.subheader(workspace_config.name)
        st.write(workspace_config.description)
        st.markdown(
            "\n".join(
                [
                    "### Start Here",
                    "- This workspace view is designed for recurring scientific review meetings.",
                    "- Start with portfolio coverage, then inspect changes since last review.",
                    "- Generate the weekly review packet before opening manager-facing decision materials.",
                    "- New researchers should run the golden demo first, then use `docs/NEW_RESEARCHER_GUIDE.md` for their own project.",
                ]
            )
        )
        st.dataframe(pd.DataFrame(inventory["summary"]), use_container_width=True)
        st.markdown(
            "\n".join(
                [
                    "### What Teams Use This For",
                    "- structure-guided experimental prioritization",
                    "- cross-project shortlist review",
                    "- preserving program memory across weekly decisions",
                    "- cleaner handoff between scientists, comp leads, and reviewers",
                ]
            )
        )
        st.markdown(brief_scope_markdown())
    elif page == "Program Memory":
        outputs = build_program_memory(workspace_config)
        st.text(safe_read_text(outputs["workspace_memory_summary.md"]))
        st.subheader("Attention Queue")
        st.dataframe(preview_table(safe_read_csv(outputs["workspace_attention_queue.csv"]), 200), use_container_width=True)
    elif page == "Multi-Cycle History":
        outputs = summarize_multicycle_history(workspace_config)
        st.subheader("Multi-Cycle Decision Summary")
        st.dataframe(preview_table(safe_read_csv(outputs["multicycle_decision_summary.csv"]), 200), use_container_width=True)
        st.subheader("Stable Shortlist Items")
        st.dataframe(preview_table(safe_read_csv(outputs["stable_shortlist_items.csv"]), 200), use_container_width=True)
        st.subheader("Repeatedly Unresolved Items")
        st.dataframe(preview_table(safe_read_csv(outputs["repeatedly_unresolved_items.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["multicycle_change_digest.md"]))
    elif page == "Outcomes":
        outputs = summarize_outcomes(workspace_config)
        st.subheader("Outcome Summary")
        st.dataframe(preview_table(safe_read_csv(outputs["outcomes_summary.csv"]), 200), use_container_width=True)
        st.subheader("Outcome-Aware Decision Summary")
        st.dataframe(preview_table(safe_read_csv(outputs["outcome_aware_decision_summary.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["outcome_digest.md"]))
    elif page == "Rationale Lineage":
        outputs = build_rationale_tracking(workspace_config)
        st.subheader("Rationale Lineage")
        st.dataframe(preview_table(safe_read_csv(outputs["rationale_lineage.csv"]), 200), use_container_width=True)
        st.subheader("Rationale Changes")
        st.dataframe(preview_table(safe_read_csv(outputs["rationale_change_log.csv"]), 200), use_container_width=True)
    elif page == "Template Effectiveness":
        outputs = summarize_template_effectiveness(workspace_config)
        st.subheader("Template Effectiveness")
        st.dataframe(preview_table(safe_read_csv(outputs["template_effectiveness_summary.csv"]), 200), use_container_width=True)
        st.subheader("Effectiveness by Cycle")
        st.dataframe(preview_table(safe_read_csv(outputs["template_effectiveness_by_cycle.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["workflow_effectiveness_digest.md"]))
    elif page == "Workflow Metrics":
        outputs = summarize_workflow_metrics(workspace_config)
        st.subheader("Workflow Metrics")
        st.dataframe(preview_table(safe_read_csv(outputs["workflow_metrics.csv"]), 200), use_container_width=True)
        st.subheader("Cycle Operational Metrics")
        st.dataframe(preview_table(safe_read_csv(outputs["cycle_operational_metrics.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["closure_summary.md"]))
    elif page == "Execution Plans":
        st.subheader("Execution Plans")
        plans_dir = workspace_config.output_dir / "execution_plans"
        if not plans_dir.exists():
            st.info("No execution plans exist yet.")
        else:
            plans = sorted(path.name for path in plans_dir.iterdir() if path.is_dir())
            if not plans:
                st.info("No execution plans found.")
            else:
                selected_plan = st.selectbox("Execution Plan", plans)
                plan_dir = plans_dir / selected_plan
                st.text(safe_read_text(plan_dir / "execution_plan_summary.md"))
                st.dataframe(preview_table(safe_read_csv(plan_dir / "execution_plan.csv"), 200), use_container_width=True)
    elif page == "Execution Tasks":
        st.subheader("Follow-up Tasks")
        plans_dir = workspace_config.output_dir / "execution_plans"
        if not plans_dir.exists():
            st.info("No execution tasks exist yet.")
        else:
            tasks_dfs = []
            for plan_dir in plans_dir.iterdir():
                if plan_dir.is_dir() and (plan_dir / "followup_tasks.csv").exists():
                    tasks_dfs.append(safe_read_csv(plan_dir / "followup_tasks.csv"))
            if tasks_dfs:
                all_tasks = pd.concat(tasks_dfs, ignore_index=True)
                # filters
                col1, col2, col3 = st.columns(3)
                owner_filter = col1.selectbox("Filter by Owner", ["All"] + all_tasks["owner"].astype(str).unique().tolist())
                status_filter = col2.selectbox("Filter by Status", ["All"] + all_tasks["status"].astype(str).unique().tolist())
                role_filter = col3.selectbox("Filter by Role", ["All"] + all_tasks["owner_role"].astype(str).unique().tolist())
                
                filtered = all_tasks.copy()
                if owner_filter != "All": filtered = filtered[filtered["owner"].astype(str) == owner_filter]
                if status_filter != "All": filtered = filtered[filtered["status"].astype(str) == status_filter]
                if role_filter != "All": filtered = filtered[filtered["owner_role"].astype(str) == role_filter]
                
                st.dataframe(preview_table(filtered, 500), use_container_width=True)
            else:
                st.info("No tasks found in execution plans.")
    elif page == "Action-to-Outcome Trace":
        from src.action_outcome_trace import build_action_outcome_trace
        outputs = build_action_outcome_trace(workspace_config)
        st.subheader("Action-to-Outcome Trace")
        st.dataframe(preview_table(safe_read_csv(outputs["action_outcome_trace.csv"]), 200), use_container_width=True)
        st.subheader("Execution to Outcome Summary")
        st.dataframe(preview_table(safe_read_csv(outputs["execution_to_outcome_summary.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["followup_path_trace.md"]))
    elif page == "Execution Metrics":
        from src.execution_metrics import summarize_execution_metrics
        outputs = summarize_execution_metrics(workspace_config)
        st.subheader("Execution Metrics")
        st.dataframe(preview_table(safe_read_csv(outputs["execution_metrics.csv"]), 200), use_container_width=True)
        st.subheader("Roles & Template usage")
        st.dataframe(preview_table(safe_read_csv(outputs["execution_metrics_by_template.csv"]), 200), use_container_width=True)
        st.subheader("Blocked Items")
        st.dataframe(preview_table(safe_read_csv(outputs["blocked_reasons_summary.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["operational_digest.md"]))
    elif page == "Retrospective Reports":
        st.subheader("Retrospective Reports")
        
        # Generation UI
        with st.expander("Generate New Retrospective", expanded=False):
            from src.retrospective_templates import load_retrospective_templates
            from src.retrospective_reporting import build_retrospective_report
            
            templates = load_retrospective_templates()
            if not templates:
                st.warning("No retrospective templates found in data/retrospective_templates.yaml")
            else:
                template_map = {t.label: t.template_id for t in templates}
                selected_label = st.selectbox("Retrospective Template", list(template_map.keys()))
                if st.button("Generate Retrospective Report"):
                    with st.spinner("Synthesizing patterns and building report..."):
                        results = build_retrospective_report(workspace_config, template_map[selected_label])
                        st.success(f"Report generated: {selected_label}")
                        st.balloons()
        
        st.divider()
        
        retro_dir = workspace_config.output_dir / "retrospectives"
        if not retro_dir.exists():
            st.info("No retrospective reports exist yet.")
        else:
            retros = sorted(path.name for path in retro_dir.iterdir() if path.is_dir())
            if not retros:
                st.info("No retrospectives found.")
            else:
                selected_retro = st.selectbox("Report", retros)
                report_dir = retro_dir / selected_retro
                st.text(safe_read_text(report_dir / "retrospective_report.md"))
                st.subheader("Role Views")
                cols = st.columns(3)
                if (report_dir / "retrospective_manager.md").exists():
                    cols[0].markdown("**Manager View**")
                    cols[0].text(safe_read_text(report_dir / "retrospective_manager.md"))
                if (report_dir / "retrospective_comp_lead.md").exists():
                    cols[1].markdown("**Comp Lead View**")
                    cols[1].text(safe_read_text(report_dir / "retrospective_comp_lead.md"))
                if (report_dir / "retrospective_scientist.md").exists():
                    cols[2].markdown("**Scientist View**")
                    cols[2].text(safe_read_text(report_dir / "retrospective_scientist.md"))
                st.subheader("Outlines")
                st.markdown("**Meeting Outline**")
                st.text(safe_read_text(report_dir / "meeting_outline.md"))
                st.markdown("**Slide Outline**")
                st.text(safe_read_text(report_dir / "slide_outline.md"))
    elif page == "Pattern Synthesis Digest":
        from src.pattern_synthesis import synthesize_patterns
        outputs = synthesize_patterns(workspace_config.output_dir)
        st.subheader("Pattern Synthesis Digest")
        st.dataframe(preview_table(safe_read_csv(outputs["pattern_synthesis.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["pattern_digest.md"]))
    elif page == "Pilot Readiness":
        from src.pilot_deployment import check_pilot_readiness
        outputs = check_pilot_readiness(workspace_config)
        st.subheader("Pilot Readiness")
        st.text(safe_read_text(outputs["pilot_readiness_report.md"]))
        st.dataframe(preview_table(safe_read_csv(outputs["deployment_checklist.csv"]), 200), use_container_width=True)
    elif page == "Role Workflow Packs":
        from src.role_workflows import export_role_workflows
        outputs = export_role_workflows(workspace_config)
        st.subheader("Role Workflow Packs")
        manifest = safe_read_csv(outputs["role_workflow_manifest.csv"])
        if not manifest.empty:
            role_map = dict(zip(manifest["role_name"], manifest["file_name"]))
            selected_role = st.selectbox("Role", list(role_map.keys()))
            st.text(safe_read_text(outputs[role_map[selected_role]]))
    elif page == "Evaluation Pack":
        from src.evaluation_pack import create_evaluation_pack
        outputs = create_evaluation_pack(workspace_config)
        st.subheader("Commercial Evaluation Pack")
        st.markdown("**Evaluation Guide**")
        st.text(safe_read_text(outputs["PILOT_EVALUATION_GUIDE.md"]))
        st.markdown("**Questions**")
        st.text(safe_read_text(outputs["evaluation_questions.md"]))
    elif page == "Workspace Evaluation":
        from src.workspace_evaluation import build_workspace_evaluation_sequence
        outputs = build_workspace_evaluation_sequence(workspace_config)
        st.subheader("Workspace Evaluation Sequence")
        st.text(safe_read_text(outputs["workspace_evaluation_plan.md"]))
        st.dataframe(preview_table(safe_read_csv(outputs["evaluation_sequence.csv"]), 200), use_container_width=True)
    
    # 2. Analysis
    elif page == "Variant Explorer" and selected_project_path is not None:
        tables = load_project_tables(selected_project_path)
        inventory = build_project_inventory(selected_project_path)
        _render_variant_explorer(st, tables, inventory)
    elif page == "Cross-Allele Comparison" and selected_project_path is not None:
        tables = load_project_tables(selected_project_path)
        _render_cross_allele(st, tables)
    elif page == "Scenario Analysis" and selected_project_path is not None:
        tables = load_project_tables(selected_project_path)
        templates = load_scenario_templates(repo_or_resource_path("data", "scenario_templates.yaml"))
        scenario_a = _scenario_controls(st.sidebar, "Scenario A", templates, tables)
        _render_scenario_analysis(st, selected_project_path, tables, scenario_a)
    elif page == "Hypotheses" and selected_project_path is not None:
        tables = load_project_tables(selected_project_path)
        _render_hypotheses(st, tables)

    # 3. Review Meeting
    elif page == "Decision Packets" and selected_project_path is not None:
        from src.decision_packet import generate_workspace_decision_packet
        if st.button("Generate Workspace Decision Packet"):
            packet_dir = generate_workspace_decision_packet(workspace_config)
            st.success(f"Wrote {packet_dir}")

    # 6. Calibration
    elif page == "External Benchmarking":
        from src.benchmark_schema import load_benchmark_templates
        from src.benchmarking import run_benchmark_comparison
        st.subheader("External Benchmarking")
        st.info("Compare internal structural evidence against external ground-truth datasets (e.g. IEDB).")
        
        templates = load_benchmark_templates()
        if not templates:
            st.warning("No benchmark templates found.")
        else:
            template_map = {t.label: t for t in templates}
            selected_label = st.selectbox("Benchmark Template", list(template_map.keys()))
            template = template_map[selected_label]
            
            st.markdown(f"**Description**: {template.description}")
            st.markdown(f"**Source**: {template.data_source}")
            
            data_path = st.text_input("External CSV Path", placeholder="path/to/benchmark_data.csv")
            if st.button("Run Comparison"):
                if not data_path:
                    st.error("Please provide a path to the external data CSV.")
                else:
                    try:
                        results = run_benchmark_comparison(workspace_config, template.benchmark_id, Path(data_path))
                        st.success("Comparison complete.")
                        st.text(safe_read_text(results["benchmark_report.md"]))
                        st.dataframe(preview_table(safe_read_csv(results["benchmark_comparison.csv"]), 500), use_container_width=True)
                    except Exception as e:
                        st.error(f"Error running comparison: {e}")

    # 7. Playbooks & Robustness
    elif page == "Scenario Playbooks":
        from src.playbook_schema import load_playbooks
        from src.scenario_playbooks import run_playbook
        st.subheader("Scenario Playbooks")
        st.info("Reusable prioritization frames with saved weights, filters, and thresholds.")
        
        playbooks = load_playbooks()
        if not playbooks:
            st.warning("No playbooks found in data/playbook_templates.yaml")
        else:
            pb_map = {p.display_name: p for p in playbooks}
            selected_name = st.selectbox("Select Playbook", list(pb_map.keys()))
            pb = pb_map[selected_name]
            
            st.markdown(f"**Description**: {pb.description}")
            st.markdown(f"**Intended Use**: {pb.intended_use}")
            with st.expander("Assumptions & Settings"):
                st.json(pb.to_dict())
            
            if st.button("Run Playbook"):
                inventory = build_workspace_inventory(workspace_config)
                combined_tables = _get_combined_workspace_tables(workspace_config, inventory)
                if not combined_tables["priority"].empty:
                    res = run_playbook(workspace_config.output_dir, pb.playbook_id, combined_tables, workspace_config.output_dir / "playbooks" / pb.playbook_id)
                    st.success("Playbook run complete.")
                    st.text(res["notes_markdown"])
                    st.dataframe(preview_table(res["ranked_variants"], 500), use_container_width=True)
                else:
                    st.error("No project data available in this workspace.")

    elif page == "Sensitivity Testing":
        from src.playbook_schema import load_playbooks
        from src.sensitivity_testing import run_sensitivity_suite
        st.subheader("Sensitivity Testing")
        st.info("Analyze how prioritization shifts when thresholds or assumptions are perturbed.")
        
        playbooks = load_playbooks()
        pb_map = {p.display_name: p for p in playbooks}
        selected_name = st.selectbox("Select Base Playbook", list(pb_map.keys()))
        
        if st.button("Run Sensitivity Suite"):
            inventory = build_workspace_inventory(workspace_config)
            combined_tables = _get_combined_workspace_tables(workspace_config, inventory)
            if not combined_tables["priority"].empty:
                with st.spinner("Running perturbations..."):
                    res = run_sensitivity_suite(workspace_config.output_dir, pb_map[selected_name].playbook_id, combined_tables)
                    st.success("Sensitivity suite complete.")
                    st.markdown(res["summary_markdown"])
            else:
                st.error("No project data available.")

    elif page == "Robustness Summary":
        from src.decision_robustness import compute_decision_robustness
        st.subheader("Decision Robustness")
        st.info("Highlights variants that remain stable (robust) or fragile across multiple scenarios.")
        
        sensitivity_dir = workspace_config.output_dir / "sensitivity"
        if not sensitivity_dir.exists():
            st.warning("Run a Sensitivity Suite first to generate robustness data.")
        else:
            runs = sorted([d.name for d in sensitivity_dir.iterdir() if d.is_dir()], reverse=True)
            if not runs:
                st.warning("No sensitivity runs found.")
            else:
                selected_run = st.selectbox("Select Sensitivity Run", runs)
                run_path = sensitivity_dir / selected_run
                
                results = []
                for subdir in run_path.iterdir():
                    if subdir.is_dir() and (subdir / "scenario_ranked_variants.csv").exists():
                        results.append({
                            "ranked_variants": safe_read_csv(subdir / "scenario_ranked_variants.csv")
                        })
                
                if results:
                    if st.button("Compute Robustness"):
                        robustness = compute_decision_robustness(results, run_path / "robustness")
                        st.success("Robustness computation complete.")
                        st.markdown(robustness["robustness_digest.md"])
                        st.dataframe(preview_table(robustness["robustness_summary.csv"], 500), use_container_width=True)
                else:
                    st.error("Invalid sensitivity run directory structure.")

    elif page == "Playbook Comparison":
        from src.playbook_schema import load_playbooks
        from src.playbook_compare import compare_playbooks
        st.subheader("Playbook Comparison")
        st.info("Directly compare the prioritizations of two different analytical frames.")
        
        playbooks = load_playbooks()
        pb_names = [p.display_name for p in playbooks]
        col1, col2 = st.columns(2)
        pb_a = col1.selectbox("Playbook A", pb_names, index=0)
        pb_b = col2.selectbox("Playbook B", pb_names, index=1 if len(pb_names) > 1 else 0)
        
        if st.button("Compare Playbooks"):
            pb_map = {p.display_name: p.playbook_id for p in playbooks}
            inventory = build_workspace_inventory(workspace_config)
            combined_tables = _get_combined_workspace_tables(workspace_config, inventory)
            if not combined_tables["priority"].empty:
                res = compare_playbooks(workspace_config.output_dir, pb_map[pb_a], pb_map[pb_b], combined_tables)
                st.success("Comparison complete.")
                st.markdown(safe_read_text(res["playbook_comparison_summary.md"]))
                st.subheader("Rank Differences")
                st.dataframe(preview_table(res["rank_diff"], 500), use_container_width=True)
            else:
                st.error("No project data available.")

    # 8. Collaborative Consensus
    elif page == "Reviewer Judgments":
        st.subheader("Reviewer Judgments")
        st.info("Structured independent assessments from team members.")
        log_path = workspace_config.output_dir / "program_memory" / "reviewer_judgments.csv"
        if not log_path.exists():
            st.warning("No reviewer judgments imported yet.")
        else:
            st.dataframe(preview_table(safe_read_csv(log_path), 500), use_container_width=True)

    elif page == "Consensus Summary":
        from src.consensus_analysis import build_consensus_summaries
        from src.disagreement_drivers import analyze_disagreement_drivers
        st.subheader("Consensus Summary")
        
        if st.button("Summarize Consensus"):
            outputs = build_consensus_summaries(workspace_config)
            analyze_disagreement_drivers(workspace_config)
            st.success("Consensus analysis complete.")
            
        summary_path = workspace_config.output_dir / "program_memory" / "consensus_summary.csv"
        if summary_path.exists():
            st.dataframe(preview_table(safe_read_csv(summary_path), 500), use_container_width=True)
            
            st.subheader("Disputed Items")
            disputed_path = workspace_config.output_dir / "program_memory" / "disputed_items.csv"
            if disputed_path.exists():
                st.dataframe(preview_table(safe_read_csv(disputed_path), 200), use_container_width=True)
                
            st.subheader("Disagreement Drivers")
            drivers_path = workspace_config.output_dir / "program_memory" / "disagreement_drivers.csv"
            if drivers_path.exists():
                st.dataframe(preview_table(safe_read_csv(drivers_path), 200), use_container_width=True)

    elif page == "Human Robustness":
        from src.human_robustness import build_human_robustness_summary
        st.subheader("Human Robustness")
        st.info("Measures how stable human judgment is across different reviewers and roles.")
        
        if st.button("Build Human Robustness Summary"):
            build_human_robustness_summary(workspace_config)
            st.success("Summary built.")
            
        robust_path = workspace_config.output_dir / "program_memory" / "human_robustness_summary.csv"
        if robust_path.exists():
            st.dataframe(preview_table(safe_read_csv(robust_path), 500), use_container_width=True)

    elif page == "Combined Robustness":
        from src.combined_robustness import build_combined_robustness
        st.subheader("Combined Robustness")
        st.info("Maps analytical evidence stability against reviewer consensus.")
        
        if st.button("Compute Combined Robustness"):
            build_combined_robustness(workspace_config)
            st.success("Combined analysis complete.")
            
        combined_path = workspace_config.output_dir / "program_memory" / "combined_robustness.csv"
        if combined_path.exists():
            st.dataframe(preview_table(safe_read_csv(combined_path), 500), use_container_width=True)
            
            st.subheader("Decision Attention Queue")
            queue_path = workspace_config.output_dir / "program_memory" / "decision_attention_queue.csv"
            if queue_path.exists():
                st.dataframe(preview_table(safe_read_csv(queue_path), 200), use_container_width=True)

    elif page == "Decision Lineage":
        outputs = build_decision_history(workspace_config)
        st.subheader("Decision Lineage")
        st.dataframe(preview_table(safe_read_csv(outputs["decision_lineage.csv"]), 200), use_container_width=True)
        st.subheader("Carry-Forward Items")
        st.dataframe(preview_table(safe_read_csv(outputs["carried_forward_items.csv"]), 200), use_container_width=True)
    elif page == "Review Cycles":
        outputs = summarize_review_cycles(workspace_config)
        cycle_df = safe_read_csv(outputs["cycle_summary.csv"])
        st.subheader("Cycle Summary")
        st.dataframe(preview_table(cycle_df, 200), use_container_width=True)
        if not cycle_df.empty and len(cycle_df) >= 2:
            cycle_names = cycle_df["cycle_id"].astype(str).tolist()
            current_cycle = st.selectbox("Current cycle", cycle_names, index=len(cycle_names) - 1)
            previous_options = [name for name in cycle_names if name != current_cycle]
            previous_cycle = st.selectbox("Previous cycle", previous_options, index=max(len(previous_options) - 1, 0))
            if st.button("Compare review cycles"):
                compare_outputs = compare_review_cycles(workspace_config, current_cycle, previous_cycle)
                st.dataframe(preview_table(safe_read_csv(compare_outputs["cycle_to_cycle_comparison.csv"]), 200), use_container_width=True)
                st.text(safe_read_text(compare_outputs["cycle_change_log.md"]))
        else:
            st.info("Generate at least two workspace review packets to compare cycles.")
    elif page == "Recurring Questions":
        outputs = build_recurring_patterns(workspace_config)
        st.subheader("Recurring Questions")
        st.dataframe(preview_table(safe_read_csv(outputs["recurring_questions.csv"]), 200), use_container_width=True)
        st.subheader("Recurring Patterns")
        st.dataframe(preview_table(safe_read_csv(outputs["recurring_patterns.csv"]), 200), use_container_width=True)
        st.text(safe_read_text(outputs["pattern_digest.md"]))
    elif page == "Workflow Templates":
        templates = load_workflow_templates(repo_or_resource_path("data", "workflow_templates.yaml"))
        selected = st.selectbox("Template", [template.name for template in templates] if templates else [""])
        template_map = {template.name: template for template in templates}
        if selected and selected in template_map:
            st.json(template_map[selected].to_dict())
        else:
            st.info("No workflow templates were available.")
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


def _get_combined_workspace_tables(config, inventory) -> dict[str, pd.DataFrame]:
    combined = {"priority": [], "panel": [], "priority_evidence": []}
    for project in inventory.get("projects", []):
        path = Path(project["project_path"])
        tables = load_project_tables(path)
        for key in combined:
            if key in tables and not tables[key].empty:
                df = tables[key].copy()
                df["project_id"] = project["project_id"]
                combined[key].append(df)
    
    return {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in combined.items()}


def _log_page_view(project_dir: Path, session_id: str, page: str) -> None:
    marker = f"page::{page}"
    if marker == getattr(_log_page_view, "_last_marker", None):
        return
    _log_page_view._last_marker = marker
    log_session_action(project_dir, session_id, "page_viewed", {"page": page})


if __name__ == "__main__":
    main()
