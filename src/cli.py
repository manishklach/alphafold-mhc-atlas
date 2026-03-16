from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

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

    exec_plan = subparsers.add_parser("execution-plan", help="Execution plan commands.")
    exec_plan_sub = exec_plan.add_subparsers(dest="exec_plan_command", required=True)
    exec_plan_build = exec_plan_sub.add_parser("build", help="Build an execution plan.")
    exec_plan_build.add_argument("--workspace", required=True)
    exec_plan_build.add_argument("--template", required=True)
    exec_plan_build.add_argument("--plan-id")

    exec_bundle = subparsers.add_parser("execution-bundle", help="Execution bundle commands.")
    exec_bundle_sub = exec_bundle.add_subparsers(dest="exec_bundle_command", required=True)
    exec_bundle_create = exec_bundle_sub.add_parser("create", help="Create an execution bundle.")
    exec_bundle_create.add_argument("--workspace", required=True)
    exec_bundle_create.add_argument("--plan-id", required=True)
    exec_bundle_create.add_argument("--bundle-id")

    ownership = subparsers.add_parser("ownership", help="Ownership tracking commands.")
    ownership_sub = ownership.add_subparsers(dest="ownership_command", required=True)
    ownership_assign = ownership_sub.add_parser("assign", help="Assign ownership to a task.")
    ownership_assign.add_argument("--workspace", required=True)
    ownership_assign.add_argument("--task-id", required=True)
    ownership_assign.add_argument("--owner", required=True)
    ownership_assign.add_argument("--role", default="unassigned")

    status_cmd = subparsers.add_parser("status", help="Status tracking commands.")
    status_sub = status_cmd.add_subparsers(dest="status_command", required=True)
    status_update = status_sub.add_parser("update", help="Update task status.")
    status_update.add_argument("--workspace", required=True)
    status_update.add_argument("--task-id", required=True)
    status_update.add_argument("--status", required=True)

    exec_metrics = subparsers.add_parser("execution-metrics", help="Execution metrics commands.")
    exec_metrics_sub = exec_metrics.add_subparsers(dest="exec_metrics_command", required=True)
    exec_metrics_summary = exec_metrics_sub.add_parser("summarize", help="Summarize execution metrics.")
    exec_metrics_summary.add_argument("--workspace", required=True)

    action_trace = subparsers.add_parser("action-trace", help="Action-to-Outcome trace commands.")
    action_trace_sub = action_trace.add_subparsers(dest="action_trace_command", required=True)
    action_trace_summary = action_trace_sub.add_parser("summarize", help="Build action-to-outcome trace.")
    action_trace_summary.add_argument("--workspace", required=True)

    retrospective = subparsers.add_parser("retrospective", help="Retrospective reporting commands.")
    retro_sub = retrospective.add_subparsers(dest="retro_command", required=True)
    retro_generate = retro_sub.add_parser("generate", help="Generate a retrospective report.")
    retro_generate.add_argument("--workspace", required=True)
    retro_generate.add_argument("--template", required=True)
    retro_generate.add_argument("--report-id")

    retro_patterns = retro_sub.add_parser("patterns", help="Synthesize recurring patterns.")
    retro_patterns.add_argument("--workspace", required=True)

    pilot_readiness = subparsers.add_parser("pilot-readiness", help="Pilot deployment readiness commands.")
    pilot_readiness_sub = pilot_readiness.add_subparsers(dest="pilot_readiness_command", required=True)
    pilot_readiness_check = pilot_readiness_sub.add_parser("check", help="Check pilot deployment readiness.")
    pilot_readiness_check.add_argument("--workspace", required=True)

    setup_pack = subparsers.add_parser("setup-pack", help="Setup pack commands.")
    setup_pack_sub = setup_pack.add_subparsers(dest="setup_pack_command", required=True)
    setup_pack_create = setup_pack_sub.add_parser("create", help="Create a portable setup pack.")
    setup_pack_create.add_argument("--workspace", required=True)
    setup_pack_create.add_argument("--pack-id")

    role_workflow = subparsers.add_parser("role-workflow", help="Role-based operating workflow commands.")
    role_workflow_sub = role_workflow.add_subparsers(dest="role_workflow_command", required=True)
    role_workflow_export = role_workflow_sub.add_parser("export", help="Export role workflow packs.")
    role_workflow_export.add_argument("--workspace", required=True)
    role_workflow_export.add_argument("--role", default=None)

    eval_pack = subparsers.add_parser("evaluation-pack", help="Commercial evaluation pack commands.")
    eval_pack_sub = eval_pack.add_subparsers(dest="eval_pack_command", required=True)
    eval_pack_create = eval_pack_sub.add_parser("create", help="Create an evaluation pack.")
    eval_pack_create.add_argument("--workspace", required=True)

    ws_eval = subparsers.add_parser("workspace-evaluation", help="Workspace evaluation flow commands.")
    ws_eval_sub = ws_eval.add_subparsers(dest="ws_eval_command", required=True)
    ws_eval_build = ws_eval_sub.add_parser("build", help="Build a full evaluation sequence.")
    ws_eval_build.add_argument("--workspace", required=True)

    benchmark = subparsers.add_parser("benchmark", help="External benchmarking commands.")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_compare = benchmark_sub.add_parser("compare", help="Compare internal evidence against external benchmark.")
    benchmark_compare.add_argument("--workspace", required=True)
    benchmark_compare.add_argument("--benchmark-id", required=True)
    benchmark_compare.add_argument("--data", required=True, help="Path to external benchmark CSV.")

    playbook = subparsers.add_parser("playbook", help="Scenario playbook commands.")
    playbook_sub = playbook.add_subparsers(dest="playbook_command", required=True)
    playbook_list = playbook_sub.add_parser("list", help="List available playbooks.")
    playbook_run = playbook_sub.add_parser("run", help="Run a playbook for a workspace.")
    playbook_run.add_argument("--workspace", required=True)
    playbook_run.add_argument("--name", required=True)
    playbook_compare = playbook_sub.add_parser("compare", help="Compare two playbooks.")
    playbook_compare.add_argument("--workspace", required=True)
    playbook_compare.add_argument("--a", required=True)
    playbook_compare.add_argument("--b", required=True)

    sensitivity = subparsers.add_parser("sensitivity", help="Sensitivity testing commands.")
    sensitivity_sub = sensitivity.add_subparsers(dest="sensitivity_command", required=True)
    sensitivity_run = sensitivity_sub.add_parser("run", help="Run sensitivity suite for a playbook.")
    sensitivity_run.add_argument("--workspace", required=True)
    sensitivity_run.add_argument("--playbook", required=True)

    robustness = subparsers.add_parser("robustness", help="Decision robustness commands.")
    robustness_sub = robustness.add_subparsers(dest="robustness_command", required=True)
    robustness_summarize = robustness_sub.add_parser("summarize", help="Summarize robustness across sensitivity runs.")
    robustness_summarize.add_argument("--workspace", required=True)
    robustness_summarize.add_argument("--playbook", required=True)

    judgments = subparsers.add_parser("judgments", help="Reviewer judgment commands.")
    judgments_sub = judgments.add_subparsers(dest="judgments_command", required=True)
    judgments_import = judgments_sub.add_parser("import", help="Import reviewer judgments from CSV.")
    judgments_import.add_argument("--workspace", required=True)
    judgments_import.add_argument("--file", required=True)

    consensus = subparsers.add_parser("consensus", help="Consensus and disagreement commands.")
    consensus_sub = consensus.add_subparsers(dest="consensus_command", required=True)
    consensus_summarize = consensus_sub.add_parser("summarize", help="Summarize consensus and analyze disagreement.")
    consensus_summarize.add_argument("--workspace", required=True)

    rev_pack = subparsers.add_parser("reviewer-pack", help="Reviewer pack commands.")
    rev_pack_sub = rev_pack.add_subparsers(dest="rev_pack_command", required=True)
    rev_pack_create = rev_pack_sub.add_parser("create", help="Create an independent reviewer pack.")
    rev_pack_create.add_argument("--workspace", required=True)
    rev_pack_create.add_argument("--pack-id", required=True)

    con_meeting = subparsers.add_parser("consensus-meeting", help="Consensus meeting commands.")
    con_meeting_sub = con_meeting.add_subparsers(dest="con_meeting_command", required=True)
    con_meeting_create = con_meeting_sub.add_parser("create", help="Create a consensus meeting pack.")
    con_meeting_create.add_argument("--workspace", required=True)
    con_meeting_create.add_argument("--meeting-id", required=True)

    exec_brief = subparsers.add_parser("executive-brief", help="Executive brief commands.")
    exec_brief_sub = exec_brief.add_subparsers(dest="exec_brief_command", required=True)
    exec_brief_create = exec_brief_sub.add_parser("create", help="Generate a deterministic executive brief.")
    exec_brief_create.add_argument("--workspace", required=True)
    exec_brief_create.add_argument("--brief-id")

    final_handoff = subparsers.add_parser("final-handoff", help="Final handoff automation commands.")
    final_handoff_sub = final_handoff.add_subparsers(dest="final_handoff_command", required=True)
    final_handoff_build = final_handoff_sub.add_parser("build", help="Build a final workspace handoff bundle.")
    final_handoff_build.add_argument("--workspace", required=True)
    final_handoff_build.add_argument("--handoff-id")

    portfolio = subparsers.add_parser("portfolio", help="Portfolio prioritization commands.")
    portfolio_sub = portfolio.add_subparsers(dest="portfolio_command", required=True)
    portfolio_agg = portfolio_sub.add_parser("aggregate", help="Aggregate portfolio candidates.")
    portfolio_agg.add_argument("--workspace", required=True)
    
    portfolio_prio = portfolio_sub.add_parser("prioritize", help="Run capacity-aware prioritization.")
    portfolio_prio.add_argument("--workspace", required=True)
    portfolio_prio.add_argument("--mode", default="evidence_first_capacity_mode")
    
    portfolio_comp = portfolio_sub.add_parser("compare", help="Compare portfolio modes.")
    portfolio_comp.add_argument("--workspace", required=True)
    portfolio_comp.add_argument("--a", required=True)
    portfolio_comp.add_argument("--b", required=True)
    
    queue = subparsers.add_parser("queue", help="Attention queue commands.")
    queue_sub = queue.add_subparsers(dest="queue_command", required=True)
    queue_build = queue_sub.add_parser("build", help="Build attention and escalation queues.")
    queue_build.add_argument("--workspace", required=True)

    org = subparsers.add_parser("org", help="Organization-level commands.")
    org_sub = org.add_subparsers(dest="org_command", required=True)
    org_agg = org_sub.add_parser("aggregate", help="Aggregate data across workspaces.")
    org_agg.add_argument("--workspace-root", required=True)
    org_agg.add_argument("--output", required=True)
    org_retro = org_sub.add_parser("retrospective", help="Generate organization retrospective.")
    org_retro.add_argument("--workspace-root", required=True)
    org_retro.add_argument("--output", required=True)
    org_retro.add_argument("--template", default="quarterly_operating_review")
    org_health = org_sub.add_parser("health", help="Summarize organization decision health.")
    org_health.add_argument("--workspace-root", required=True)
    org_health.add_argument("--output", required=True)
    org_packet = org_sub.add_parser("packet", help="Create organization operating review packet.")
    org_packet.add_argument("--workspace-root", required=True)
    org_packet.add_argument("--output", required=True)
    org_packet.add_argument("--packet-id")

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
    if args.command == "execution-plan" and args.exec_plan_command == "build":
        from .execution_plan import build_execution_plan
        outputs = build_execution_plan(args.workspace, args.template, args.plan_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0
    if args.command == "execution-bundle" and args.exec_bundle_command == "create":
        from .execution_bundle import build_execution_bundle
        path = build_execution_bundle(args.workspace, args.plan_id, args.bundle_id)
        print(path)
        return 0
    if args.command == "ownership" and args.ownership_command == "assign":
        from .ownership import assign_ownership
        path = assign_ownership(args.workspace, args.task_id, args.owner, args.role)
        print(path)
        return 0
    if args.command == "status" and args.status_command == "update":
        from .status_tracking import update_task_status
        path = update_task_status(args.workspace, args.task_id, args.status)
        print(path)
        return 0
    if args.command == "execution-metrics" and args.exec_metrics_command == "summarize":
        from .execution_metrics import summarize_execution_metrics
        outputs = summarize_execution_metrics(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0
    if args.command == "action-trace" and args.action_trace_command == "summarize":
        from .action_outcome_trace import build_action_outcome_trace
        outputs = build_action_outcome_trace(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0
    if args.command == "retrospective" and args.retro_command == "generate":
        from .retrospective_reporting import build_retrospective_report
        outputs = build_retrospective_report(args.workspace, args.template, args.report_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0
    if args.command == "retrospective" and args.retro_command == "patterns":
        from .pattern_synthesis import synthesize_patterns
        config = load_workspace_config(args.workspace)
        outputs = synthesize_patterns(config.output_dir)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "pilot-readiness" and args.pilot_readiness_command == "check":
        from .pilot_deployment import check_pilot_readiness
        outputs = check_pilot_readiness(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "setup-pack" and args.setup_pack_command == "create":
        from .setup_pack import create_setup_pack
        outputs = create_setup_pack(args.workspace, args.pack_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "role-workflow" and args.role_workflow_command == "export":
        from .role_workflows import export_role_workflows
        outputs = export_role_workflows(args.workspace, args.role)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "evaluation-pack" and args.eval_pack_command == "create":
        from .evaluation_pack import create_evaluation_pack
        outputs = create_evaluation_pack(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "workspace-evaluation" and args.ws_eval_command == "build":
        from .workspace_evaluation import build_workspace_evaluation_sequence
        outputs = build_workspace_evaluation_sequence(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "benchmark" and args.benchmark_command == "compare":
        from .benchmarking import run_benchmark_comparison
        outputs = run_benchmark_comparison(args.workspace, args.benchmark_id, Path(args.data))
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "playbook" and args.playbook_command == "list":
        from .playbook_schema import load_playbooks
        playbooks = load_playbooks()
        for p in playbooks:
            print(f"- {p.playbook_id}: {p.display_name} ({p.intended_use})")
        return 0

    if args.command == "playbook" and args.playbook_command == "run":
        from .scenario_playbooks import run_playbook
        config = load_workspace_config(args.workspace)
        inventory = build_workspace_inventory(config)
        # Combine tables from all projects
        tables = _combine_project_tables(inventory)
        outputs = run_playbook(config.output_dir, args.name, tables, config.output_dir / "playbooks" / args.name)
        print(json.dumps({k: str(v) for k, v in outputs.items() if isinstance(v, (str, Path))}, indent=2))
        return 0

    if args.command == "playbook" and args.playbook_command == "compare":
        from .playbook_compare import compare_playbooks
        config = load_workspace_config(args.workspace)
        inventory = build_workspace_inventory(config)
        tables = _combine_project_tables(inventory)
        outputs = compare_playbooks(config.output_dir, args.a, args.b, tables)
        print(json.dumps({k: str(v) for k, v in outputs.items() if isinstance(v, (str, Path))}, indent=2))
        return 0

    if args.command == "sensitivity" and args.sensitivity_command == "run":
        from .sensitivity_testing import run_sensitivity_suite
        config = load_workspace_config(args.workspace)
        inventory = build_workspace_inventory(config)
        tables = _combine_project_tables(inventory)
        outputs = run_sensitivity_suite(config.output_dir, args.playbook, tables)
        print(json.dumps({k: str(v) for k, v in outputs.items() if isinstance(v, (str, Path))}, indent=2))
        return 0

    if args.command == "robustness" and args.robustness_command == "summarize":
        from .sensitivity_testing import run_sensitivity_suite
        from .decision_robustness import compute_decision_robustness
        config = load_workspace_config(args.workspace)
        inventory = build_workspace_inventory(config)
        tables = _combine_project_tables(inventory)
        # Run sensitivity first to ensure we have data
        res = run_sensitivity_suite(config.output_dir, args.playbook, tables)
        outputs = compute_decision_robustness(res["results"], config.output_dir / "program_memory")
        print(json.dumps({k: str(v) for k, v in outputs.items() if isinstance(v, (str, Path))}, indent=2))
        return 0

    if args.command == "judgments" and args.judgments_command == "import":
        from .reviewer_judgments import import_reviewer_judgments
        path = import_reviewer_judgments(args.workspace, Path(args.file))
        print(path)
        return 0

    if args.command == "consensus" and args.consensus_command == "summarize":
        from .consensus_analysis import build_consensus_summaries
        from .disagreement_drivers import analyze_disagreement_drivers
        from .human_robustness import build_human_robustness_summary
        from .combined_robustness import build_combined_robustness
        build_consensus_summaries(args.workspace)
        analyze_disagreement_drivers(args.workspace)
        build_human_robustness_summary(args.workspace)
        outputs = build_combined_robustness(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items() if isinstance(v, (str, Path))}, indent=2))
        return 0

    if args.command == "reviewer-pack" and args.rev_pack_command == "create":
        from .reviewer_packs import create_reviewer_pack
        path = create_reviewer_pack(args.workspace, args.pack_id)
        print(path)
        return 0

    if args.command == "consensus-meeting" and args.con_meeting_command == "create":
        from .consensus_meeting import create_consensus_meeting_pack
        path = create_consensus_meeting_pack(args.workspace, args.meeting_id)
        print(path)
        return 0

    if args.command == "executive-brief" and args.exec_brief_command == "create":
        from .executive_brief import generate_executive_brief
        outputs = generate_executive_brief(args.workspace, args.brief_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "final-handoff" and args.final_handoff_command == "build":
        from .final_handoff import build_final_handoff
        outputs = build_final_handoff(args.workspace, args.handoff_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "portfolio" and args.portfolio_command == "aggregate":
        from .portfolio_aggregation import build_portfolio_aggregation
        outputs = build_portfolio_aggregation(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "portfolio" and args.portfolio_command == "prioritize":
        from .portfolio_prioritization import build_portfolio_prioritization
        outputs = build_portfolio_prioritization(args.workspace, args.mode)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "portfolio" and args.portfolio_command == "compare":
        from .portfolio_compare import compare_portfolio_modes
        outputs = compare_portfolio_modes(args.workspace, args.a, args.b)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "queue" and args.queue_command == "build":
        from .attention_queue import build_attention_queues
        outputs = build_attention_queues(args.workspace)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "org" and args.org_command == "aggregate":
        from .org_aggregation import write_org_aggregation
        outputs = write_org_aggregation(Path(args.workspace_root), Path(args.output))
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "org" and args.org_command == "retrospective":
        from .org_retrospective import build_org_retrospective
        outputs = build_org_retrospective(Path(args.workspace_root), Path(args.output), args.template)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "org" and args.org_command == "health":
        from .system_health import build_org_system_health
        outputs = build_org_system_health(Path(args.workspace_root), Path(args.output))
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "org" and args.org_command == "packet":
        from .operating_review_packet import build_operating_review_packet
        outputs = build_operating_review_packet(Path(args.workspace_root), Path(args.output), args.packet_id)
        print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2))
        return 0

    if args.command == "version":
        print(__version__)
        return 0
    parser.error("Unknown command")
    return 1


def _combine_project_tables(inventory: dict[str, object]) -> dict[str, pd.DataFrame]:
    from .app import load_project_tables
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
