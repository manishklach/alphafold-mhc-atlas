from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .annotations import add_annotation
from .app import launch_app
from .checklists import run_checklist
from .config import load_config
from .decision_history import build_decision_history
from .decision_packet import generate_project_decision_packet, generate_workspace_decision_packet
from .demo_bundle import build_demo_bundle_manifest, validate_demo
from .demo_loader import describe_demo, list_all_demos, list_demo_projects, load_demo_readme, load_demo_walkthrough, resolve_demo_project, resolve_demo_workspace
from .feedback import add_feedback
from .feedback_schema import FeedbackEntry
from .handoff_bundle import create_handoff_bundle
from .main import main as pipeline_main
from .multicycle_history import summarize_multicycle_history
from .next_actions import build_next_actions
from .outcomes import import_outcomes, summarize_outcomes
from .pilot_workflow import build_review_analytics, initialize_pilot_workflow
from .program_memory import build_program_memory
from .project_history import build_project_history
from .project_index import build_project_inventory, load_project_tables, write_project_inventory
from .rationale_tracking import build_rationale_tracking
from .review_packet import generate_project_review_packet, generate_workspace_review_packet
from .review_queue import create_review_queue_from_scenario
from .review_cycles import compare_review_cycles, summarize_review_cycles
from .resource_paths import REPO_ROOT, repo_or_resource_path
from .recurring_patterns import build_recurring_patterns
from .role_views import export_role_views
from .scenario_analysis import build_evidence_exports, compare_scenarios, export_scenario_comparison, export_scenario_result, run_scenario_analysis
from .scenario_state import ScenarioState, load_scenario_state, save_scenario_state
from .shortlist import refresh_shortlists
from .template_effectiveness import summarize_template_effectiveness
from .version import PACKAGE_NAME, __version__
from .workflow_metrics import summarize_workflow_metrics
from .workspace import load_workspace_config
from .workspace_index import build_workspace_inventory, write_workspace_inventory
from .app import load_scenario_templates
from .workflow_templates import get_workflow_template, list_workflow_templates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PACKAGE_NAME, description="Peptide-MHC Atlas CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the analysis pipeline.")
    run_parser.add_argument("--config", required=True)

    app_parser = subparsers.add_parser("app", help="Launch the interactive app.")
    app_parser.add_argument("--project")
    app_parser.add_argument("--demo")
    app_parser.add_argument("--workspace")
    app_parser.add_argument("--host", default="127.0.0.1")
    app_parser.add_argument("--port", type=int, default=8501)

    subparsers.add_parser("list-demos", help="List curated demos, including golden walkthrough demos.")

    walkthrough_parser = subparsers.add_parser("demo-walkthrough", help="Print the README and walkthrough for a demo.")
    walkthrough_parser.add_argument("demo_name")

    inventory_parser = subparsers.add_parser("inventory", help="Print project inventory as JSON.")
    inventory_parser.add_argument("project")
    inventory_parser.add_argument("--write", action="store_true")

    scenario_parser = subparsers.add_parser("scenario", help="Run a scenario from a template against an existing project.")
    scenario_parser.add_argument("--project", required=True)
    scenario_parser.add_argument("--template", required=True)
    scenario_parser.add_argument("--output-dir")

    export_parser = subparsers.add_parser("export", aliases=["export-scenario"], help="Export a saved scenario against an existing project.")
    export_parser.add_argument("--project", required=True)
    export_parser.add_argument("--scenario", required=True)
    export_parser.add_argument("--output-dir")

    report_parser = subparsers.add_parser("report", help="Show report-related paths for a project.")
    report_parser.add_argument("--project", required=True)

    validate_parser = subparsers.add_parser("validate-config", help="Validate a config file.")
    validate_parser.add_argument("config")

    env_parser = subparsers.add_parser("check-environment", help="Check runtime environment and optional app dependencies.")
    env_parser.add_argument("--json", action="store_true")

    demo_validate = subparsers.add_parser("validate-demo", help="Validate a named demo project.")
    demo_validate.add_argument("demo_name")

    demo_bundle = subparsers.add_parser("build-demo-bundle", help="Write a demo bundle manifest.")
    demo_bundle.add_argument("--output-dir", default="dist_assets")

    review_parser = subparsers.add_parser("review", help="Pilot review workflow commands.")
    review_sub = review_parser.add_subparsers(dest="review_command", required=True)
    review_init = review_sub.add_parser("init", help="Initialize a pilot workflow and review queue.")
    review_init.add_argument("--project", required=True)
    review_init.add_argument("--scenario", required=True)
    review_init.add_argument("--reviewer", default="pilot_user")

    review_queue = review_sub.add_parser("queue", help="Generate a review queue from a scenario.")
    review_queue.add_argument("--project", required=True)
    review_queue.add_argument("--scenario", required=True)
    review_queue.add_argument("--reviewer", default="pilot_user")

    review_shortlist = review_sub.add_parser("shortlist", help="Refresh shortlist artifacts from review queue.")
    review_shortlist.add_argument("--project", required=True)

    feedback_parser = subparsers.add_parser("feedback", help="Structured feedback commands.")
    feedback_sub = feedback_parser.add_subparsers(dest="feedback_command", required=True)
    feedback_add = feedback_sub.add_parser("add", help="Add a feedback entry.")
    feedback_add.add_argument("--project", required=True)
    feedback_add.add_argument("--entity-type", required=True)
    feedback_add.add_argument("--entity-id", required=True)
    feedback_add.add_argument("--reviewer-name", default="pilot_user")
    feedback_add.add_argument("--reviewer-role", default="collaborator")
    feedback_add.add_argument("--sentiment", default="neutral")
    feedback_add.add_argument("--usefulness-rating", type=int, default=3)
    feedback_add.add_argument("--clarity-rating", type=int, default=3)
    feedback_add.add_argument("--confidence-in-output", default="moderate")
    feedback_add.add_argument("--concern-type", default="other")
    feedback_add.add_argument("--comment", default="")
    feedback_add.add_argument("--requested-followup", default="")
    feedback_add.add_argument("--status", default="open")

    handoff_parser = subparsers.add_parser("handoff", help="Handoff bundle commands.")
    handoff_sub = handoff_parser.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_sub.add_parser("create", help="Create a collaborator handoff bundle.")
    handoff_create.add_argument("--project", required=True)
    handoff_create.add_argument("--bundle-id", required=True)
    handoff_create.add_argument("--scenario", action="append", dest="scenarios", required=True)

    checklist_parser = subparsers.add_parser("checklist", help="Checklist commands.")
    checklist_sub = checklist_parser.add_subparsers(dest="checklist_command", required=True)
    checklist_run = checklist_sub.add_parser("run", help="Run a checklist template.")
    checklist_run.add_argument("--project", required=True)
    checklist_run.add_argument("--template", required=True)
    checklist_run.add_argument("--reviewer", default="pilot_user")

    workspace_parser = subparsers.add_parser("workspace", help="Workspace commands.")
    workspace_sub = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_init = workspace_sub.add_parser("init", help="Validate a workspace config and write inventory.")
    workspace_init.add_argument("--config", required=True)
    workspace_inventory = workspace_sub.add_parser("inventory", help="Print workspace inventory as JSON.")
    workspace_inventory.add_argument("--workspace", required=True)
    workspace_inventory.add_argument("--write", action="store_true")

    review_packet = subparsers.add_parser("review-packet", help="Generate weekly review packets.")
    review_packet_sub = review_packet.add_subparsers(dest="review_packet_command", required=True)
    review_packet_generate = review_packet_sub.add_parser("generate", help="Generate a project or workspace review packet.")
    review_packet_generate.add_argument("--project")
    review_packet_generate.add_argument("--workspace")
    review_packet_generate.add_argument("--packet-id")
    review_packet_generate.add_argument("--workflow-template")

    decision_packet = subparsers.add_parser("decision-packet", help="Generate decision meeting packets.")
    decision_packet_sub = decision_packet.add_subparsers(dest="decision_packet_command", required=True)
    decision_packet_generate = decision_packet_sub.add_parser("generate", help="Generate a project or workspace decision packet.")
    decision_packet_generate.add_argument("--project")
    decision_packet_generate.add_argument("--workspace")
    decision_packet_generate.add_argument("--packet-id")
    decision_packet_generate.add_argument("--workflow-template")

    role_view = subparsers.add_parser("role-view", help="Role-oriented export commands.")
    role_view_sub = role_view.add_subparsers(dest="role_view_command", required=True)
    role_view_export = role_view_sub.add_parser("export", help="Export role views for a project.")
    role_view_export.add_argument("--project", required=True)
    role_view_export.add_argument("--role", choices=["scientist", "comp_lead", "manager"])

    changes = subparsers.add_parser("changes", help="Project history and change-summary commands.")
    changes_sub = changes.add_subparsers(dest="changes_command", required=True)
    changes_summary = changes_sub.add_parser("summarize", help="Build project history and change summary.")
    changes_summary.add_argument("--project", required=True)

    next_actions = subparsers.add_parser("next-actions", help="Next-action planning commands.")
    next_actions_sub = next_actions.add_subparsers(dest="next_actions_command", required=True)
    next_actions_build = next_actions_sub.add_parser("build", help="Build next actions for a project.")
    next_actions_build.add_argument("--project", required=True)

    workflow_template_parser = subparsers.add_parser("workflow-template", help="Reusable workflow template commands.")
    workflow_template_sub = workflow_template_parser.add_subparsers(dest="workflow_template_command", required=True)
    workflow_template_sub.add_parser("list", help="List workflow templates.")
    workflow_template_show = workflow_template_sub.add_parser("show", help="Show one workflow template.")
    workflow_template_show.add_argument("--name", required=True)

    history = subparsers.add_parser("history", help="Workspace program-memory commands.")
    history_sub = history.add_subparsers(dest="history_command", required=True)
    history_summary = history_sub.add_parser("summarize", help="Build workspace memory summaries.")
    history_summary.add_argument("--workspace", required=True)

    review_cycle = subparsers.add_parser("review-cycle", help="Review cycle comparison commands.")
    review_cycle_sub = review_cycle.add_subparsers(dest="review_cycle_command", required=True)
    review_cycle_compare = review_cycle_sub.add_parser("compare", help="Compare two named workspace review cycles.")
    review_cycle_compare.add_argument("--workspace", required=True)
    review_cycle_compare.add_argument("--current", required=True)
    review_cycle_compare.add_argument("--previous", required=True)

    decision_history = subparsers.add_parser("decision-history", help="Decision lineage commands.")
    decision_history_sub = decision_history.add_subparsers(dest="decision_history_command", required=True)
    decision_history_build = decision_history_sub.add_parser("build", help="Build workspace decision lineage outputs.")
    decision_history_build.add_argument("--workspace", required=True)

    outcomes_parser = subparsers.add_parser("outcomes", help="Outcome integration commands.")
    outcomes_sub = outcomes_parser.add_subparsers(dest="outcomes_command", required=True)
    outcomes_import = outcomes_sub.add_parser("import", help="Import downstream outcomes into workspace memory.")
    outcomes_import.add_argument("--workspace", required=True)
    outcomes_import.add_argument("--file", required=True)
    outcomes_summary = outcomes_sub.add_parser("summarize", help="Summarize imported downstream outcomes.")
    outcomes_summary.add_argument("--workspace", required=True)

    multicycle_parser = subparsers.add_parser("multicycle", help="Multi-cycle decision history commands.")
    multicycle_sub = multicycle_parser.add_subparsers(dest="multicycle_command", required=True)
    multicycle_summary = multicycle_sub.add_parser("summarize", help="Build multi-cycle decision summaries.")
    multicycle_summary.add_argument("--workspace", required=True)

    template_effectiveness = subparsers.add_parser("template-effectiveness", help="Workflow-template effectiveness commands.")
    template_effectiveness_sub = template_effectiveness.add_subparsers(dest="template_effectiveness_command", required=True)
    template_effectiveness_summary = template_effectiveness_sub.add_parser("summarize", help="Summarize operational workflow-template associations.")
    template_effectiveness_summary.add_argument("--workspace", required=True)

    rationale = subparsers.add_parser("rationale", help="Rationale carry-forward commands.")
    rationale_sub = rationale.add_subparsers(dest="rationale_command", required=True)
    rationale_summary = rationale_sub.add_parser("summarize", help="Build rationale lineage and rationale-change summaries.")
    rationale_summary.add_argument("--workspace", required=True)

    workflow_metrics = subparsers.add_parser("workflow-metrics", help="Operational workflow metrics commands.")
    workflow_metrics_sub = workflow_metrics.add_subparsers(dest="workflow_metrics_command", required=True)
    workflow_metrics_summary = workflow_metrics_sub.add_parser("summarize", help="Build workflow-operational metrics conservatively.")
    workflow_metrics_summary.add_argument("--workspace", required=True)

    subparsers.add_parser("version", help="Print package version.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        sys.argv = ["src.main", "--config", args.config]
        pipeline_main()
        return 0
    if args.command == "app":
        workspace = args.workspace
        demo = args.demo
        if demo and not workspace and not args.project:
            metadata = describe_demo(demo)
            if metadata.get("has_workspace") and not metadata.get("has_project"):
                workspace = str(resolve_demo_workspace(demo))
                demo = None
        launch_app(project=args.project, demo=demo, workspace=workspace, host=args.host, port=args.port)
        return 0
    if args.command == "list-demos":
        print("\n".join(list_all_demos()))
        return 0
    if args.command == "demo-walkthrough":
        parts = []
        readme = load_demo_readme(args.demo_name)
        walkthrough = load_demo_walkthrough(args.demo_name)
        if readme:
            parts.extend([readme, ""])
        if walkthrough:
            parts.extend(["# Walkthrough", "", walkthrough])
        elif not readme:
            workspace_path = resolve_demo_workspace(args.demo_name)
            parts.append(f"Demo workspace: {workspace_path}")
        print("\n".join(parts).strip())
        return 0
    if args.command == "inventory":
        project = _resolve_path(args.project)
        inventory = build_project_inventory(project)
        print(json.dumps(inventory, indent=2))
        if args.write:
            write_project_inventory(project)
        return 0
    if args.command == "scenario":
        project = _resolve_path(args.project)
        tables = load_project_tables(project)
        template = _find_template(args.template)
        result = run_scenario_analysis(template, tables)
        output_dir = _resolve_optional_output(project, args.output_dir, template.scenario_id)
        export_scenario_result(result, output_dir)
        build_evidence_exports(result, tables, output_dir)
        print(output_dir)
        return 0
    if args.command == "export":
        project = _resolve_path(args.project)
        tables = load_project_tables(project)
        scenario = load_scenario_state(_resolve_path(args.scenario))
        result = run_scenario_analysis(scenario, tables)
        output_dir = _resolve_optional_output(project, args.output_dir, scenario.scenario_id)
        export_scenario_result(result, output_dir)
        build_evidence_exports(result, tables, output_dir)
        print(output_dir)
        return 0
    if args.command == "report":
        project = _resolve_path(args.project)
        report_path = project / "analysis" / "report.md"
        inventory_path = project / "analysis" / "project_inventory.json"
        print(json.dumps({"report_path": str(report_path), "inventory_path": str(inventory_path)}, indent=2))
        return 0
    if args.command == "validate-config":
        config = load_config(args.config)
        print(f"Valid config: {config.project_name}")
        return 0
    if args.command == "check-environment":
        payload = _environment_payload()
        print(json.dumps(payload, indent=2) if args.json else _environment_text(payload))
        return 0
    if args.command == "validate-demo":
        print(json.dumps(validate_demo(args.demo_name), indent=2))
        return 0
    if args.command == "build-demo-bundle":
        path = build_demo_bundle_manifest(_resolve_path(args.output_dir))
        print(path)
        return 0
    if args.command == "review":
        project = _resolve_path(args.project)
        if args.review_command in {"init", "queue"}:
            tables = load_project_tables(project)
            template = _find_template(args.scenario)
            result = run_scenario_analysis(template, tables)
            export_dir = project / "scenario_exports" / template.scenario_id
            export_scenario_result(result, export_dir)
            build_evidence_exports(result, tables, export_dir)
            queue_path = create_review_queue_from_scenario(project, result, reviewer=args.reviewer)
            if args.review_command == "init":
                initialize_pilot_workflow(project, template.scenario_id, reviewer=args.reviewer)
            print(queue_path)
            return 0
        if args.review_command == "shortlist":
            print(refresh_shortlists(project))
            return 0
    if args.command == "feedback" and args.feedback_command == "add":
        project = _resolve_path(args.project)
        path = add_feedback(
            project,
            FeedbackEntry(
                entity_type=args.entity_type,
                entity_id=args.entity_id,
                reviewer_name=args.reviewer_name,
                reviewer_role=args.reviewer_role,
                sentiment=args.sentiment,
                usefulness_rating=args.usefulness_rating,
                clarity_rating=args.clarity_rating,
                confidence_in_output=args.confidence_in_output,
                concern_type=args.concern_type,
                free_text_comment=args.comment,
                requested_followup=args.requested_followup,
                status=args.status,
            ),
        )
        build_review_analytics(project)
        print(path)
        return 0
    if args.command == "handoff" and args.handoff_command == "create":
        project = _resolve_path(args.project)
        print(create_handoff_bundle(project, bundle_id=args.bundle_id, scenario_ids=args.scenarios))
        return 0
    if args.command == "checklist" and args.checklist_command == "run":
        project = _resolve_path(args.project)
        print(run_checklist(project, args.template, reviewer=args.reviewer))
        return 0
    if args.command == "workspace":
        if args.workspace_command == "init":
            config = load_workspace_config(args.config)
            print(write_workspace_inventory(config))
            return 0
        if args.workspace_command == "inventory":
            config = load_workspace_config(args.workspace)
            inventory = build_workspace_inventory(config)
            print(json.dumps(inventory, indent=2))
            if args.write:
                write_workspace_inventory(config)
            return 0
    if args.command == "review-packet" and args.review_packet_command == "generate":
        if args.workspace:
            print(
                generate_workspace_review_packet(
                    args.workspace,
                    packet_id=args.packet_id,
                    workflow_template_name=args.workflow_template,
                )
            )
            return 0
        if args.project:
            print(
                generate_project_review_packet(
                    _resolve_path(args.project),
                    packet_id=args.packet_id,
                    workflow_template_name=args.workflow_template,
                )
            )
            return 0
        raise SystemExit("review-packet generate requires --project or --workspace")
    if args.command == "decision-packet" and args.decision_packet_command == "generate":
        if args.workspace:
            print(
                generate_workspace_decision_packet(
                    args.workspace,
                    packet_id=args.packet_id,
                    workflow_template_name=args.workflow_template,
                )
            )
            return 0
        if args.project:
            print(
                generate_project_decision_packet(
                    _resolve_path(args.project),
                    packet_id=args.packet_id,
                    workflow_template_name=args.workflow_template,
                )
            )
            return 0
        raise SystemExit("decision-packet generate requires --project or --workspace")
    if args.command == "role-view" and args.role_view_command == "export":
        paths = export_role_views(_resolve_path(args.project))
        print(paths[args.role] if args.role else json.dumps({name: str(path) for name, path in paths.items()}, indent=2))
        return 0
    if args.command == "changes" and args.changes_command == "summarize":
        print(build_project_history(_resolve_path(args.project)))
        return 0
    if args.command == "next-actions" and args.next_actions_command == "build":
        print(build_next_actions(_resolve_path(args.project)))
        return 0
    if args.command == "workflow-template":
        if args.workflow_template_command == "list":
            print("\n".join(list_workflow_templates()))
            return 0
        print(json.dumps(get_workflow_template(args.name).to_dict(), indent=2))
        return 0
    if args.command == "history" and args.history_command == "summarize":
        outputs = build_program_memory(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "review-cycle" and args.review_cycle_command == "compare":
        outputs = compare_review_cycles(args.workspace, args.current, args.previous)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "decision-history" and args.decision_history_command == "build":
        outputs = build_decision_history(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "outcomes":
        if args.outcomes_command == "import":
            print(import_outcomes(args.workspace, args.file))
            return 0
        outputs = summarize_outcomes(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "multicycle" and args.multicycle_command == "summarize":
        outputs = summarize_multicycle_history(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "template-effectiveness" and args.template_effectiveness_command == "summarize":
        outputs = summarize_template_effectiveness(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "rationale" and args.rationale_command == "summarize":
        outputs = build_rationale_tracking(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "workflow-metrics" and args.workflow_metrics_command == "summarize":
        outputs = summarize_workflow_metrics(args.workspace)
        print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))
        return 0
    if args.command == "version":
        print(__version__)
        return 0
    parser.error("Unknown command")
    return 1


def _resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _resolve_optional_output(project: Path, output_dir: str | None, scenario_id: str) -> Path:
    if output_dir:
        return _resolve_path(output_dir)
    return project / "scenario_exports" / scenario_id


def _find_template(template_name: str) -> ScenarioState:
    templates = load_scenario_templates(repo_or_resource_path("data", "scenario_templates.yaml"))
    for template in templates:
        if template.scenario_id == template_name or template.label == template_name:
            return template
    raise SystemExit(f"Scenario template not found: {template_name}")


def _environment_payload() -> dict[str, object]:
    import platform
    import importlib.util

    deps = {name: bool(importlib.util.find_spec(name)) for name in ["yaml", "numpy", "pandas", "matplotlib", "Bio", "flask", "streamlit", "pytest"]}
    return {
        "package": PACKAGE_NAME,
        "version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": deps,
    }


def _environment_text(payload: dict[str, object]) -> str:
    lines = [
        f"{payload['package']} {payload['version']}",
        f"Python: {payload['python_version']}",
        f"Platform: {payload['platform']}",
        "Dependencies:",
    ]
    for name, available in payload["dependencies"].items():
        lines.append(f"- {name}: {'ok' if available else 'missing'}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
