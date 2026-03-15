from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

from src.data_access import preview_table, safe_read_json
from src.demo_loader import DEMO_ROOT, list_demo_projects, load_demo_readme, resolve_demo_project
from src.evidence_view import build_variant_evidence_bundle, export_variant_evidence_bundle
from src.project_index import build_project_inventory, load_project_report, load_project_tables, write_project_inventory
from src.scenario_analysis import (
    build_evidence_exports,
    compare_scenarios,
    export_scenario_comparison,
    export_scenario_result,
    run_scenario_analysis,
)
from src.scenario_state import ScenarioState, load_scenario_state, save_scenario_state


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive local analyst app for the peptide-MHC atlas.")
    parser.add_argument("--project", help="Path to an existing project output directory.", default=None)
    parser.add_argument("--demo", help="Load a curated demo project by name.", default=None)
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
    if args.write_project_inventory:
        command.append("--write-project-inventory")
    subprocess.run(command, cwd=REPO_ROOT, check=False)


def render_streamlit_app(args: argparse.Namespace) -> None:
    import streamlit as st

    st.set_page_config(page_title="Peptide-MHC Atlas", layout="wide")
    st.title("Peptide-MHC Atlas Decision Support")

    templates = load_scenario_templates(REPO_ROOT / "data" / "scenario_templates.yaml")
    source_mode = st.sidebar.radio("Source", ["Local project", "Demo project"])
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
            "Case Studies",
            "Hypotheses",
            "Reports / Exports",
        ],
    )

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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alleles", coverage["num_alleles"])
    c2.metric("Variants", coverage["num_variants"])
    c3.metric("Priority rows", coverage["prioritization_rows"])
    c4.metric("Panel rows", coverage["panel_rows"])
    st.subheader("Available modules")
    st.write(", ".join(inventory["available_modules"]))
    if inventory["notes"]:
        st.warning(" | ".join(inventory["notes"]))
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
    st.subheader("Project inventory")
    st.json(inventory)
    if st.button("Write project inventory file"):
        path = write_project_inventory(project_dir)
        st.success(f"Wrote {path}")


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


if __name__ == "__main__":
    main()
