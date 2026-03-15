from __future__ import annotations

import argparse
import csv
import html
import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, abort, current_app, render_template, request, send_file


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
EXAMPLES_ROOT = REPO_ROOT / "examples"
SECTION_LABELS = {
    "study_overview": "Study Overview",
    "within_allele_analysis": "Within-Allele Analysis",
    "cross_allele_analysis": "Cross-Allele Analysis",
    "pocket_signature_analysis": "Pocket Signature Analysis",
    "hypothesis_generation": "Hypothesis Generation",
    "caveats": "Caveats",
    "analysis": "Analysis",
    "plots": "Plots",
}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["REPO_ROOT"] = REPO_ROOT
    app.config["OUTPUTS_ROOT"] = OUTPUTS_ROOT
    app.jinja_env.filters["markdown_like"] = render_markdown_like

    @app.route("/")
    def index():
        projects = discover_projects(app.config["OUTPUTS_ROOT"])
        configs = discover_configs(EXAMPLES_ROOT)
        return render_template("index.html", projects=projects, configs=configs)

    @app.route("/run", methods=["POST"])
    def run_pipeline():
        config_path = Path(request.form.get("config_path", "")).expanduser()
        if not config_path.is_absolute():
            config_path = (REPO_ROOT / config_path).resolve()
        if not config_path.exists():
            abort(400, f"Config not found: {config_path}")

        command = [sys.executable, "-m", "src.main", "--config", str(config_path)]
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
        project_name = _read_project_name_from_config(config_path)
        project_dir = _resolve_project_dir(config_path)
        return render_template(
            "run_result.html",
            command=" ".join(command),
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            project_name=project_name,
            project_dir=project_dir.name if project_dir else None,
        )

    @app.route("/project/<project_name>")
    def project_detail(project_name: str):
        project_dir = _safe_project_dir(project_name)
        snapshot = _load_json(project_dir / "analysis" / "analysis_snapshot.json")
        report_summary = _load_json(project_dir / "analysis" / "report_summary.json")
        fallback_meta = derive_project_metadata(project_dir)
        report_text = _read_text(project_dir / "analysis" / "report.md")
        tables = list_analysis_tables(project_dir)
        plots = list_plot_files(project_dir)
        case_studies = list_case_studies(project_dir)
        categories = build_project_categories(project_dir, tables, plots, case_studies, snapshot, report_summary)
        plot_entries = [plot for plot in plots if plot.get("status") == "ok"]
        return render_template(
            "project_detail.html",
            project_name=project_name,
            snapshot=snapshot,
            report_summary=report_summary,
            fallback_meta=fallback_meta,
            report_text=report_text,
            tables=tables,
            plots=plot_entries,
            case_studies=case_studies,
            categories=categories,
        )

    @app.route("/project/<project_name>/table/<table_name>")
    def table_view(project_name: str, table_name: str):
        project_dir = _safe_project_dir(project_name)
        table_path = project_dir / "analysis" / table_name
        if not table_path.exists() or table_path.suffix.lower() != ".csv":
            abort(404)
        headers, rows = load_csv_preview(table_path)
        return render_template(
            "table_view.html",
            project_name=project_name,
            table_name=table_name,
            headers=headers,
            rows=rows,
            table_path=table_path,
        )

    @app.route("/project/<project_name>/report")
    def report_view(project_name: str):
        project_dir = _safe_project_dir(project_name)
        report_path = project_dir / "analysis" / "report.md"
        if not report_path.exists():
            abort(404)
        return render_template(
            "report_view.html",
            project_name=project_name,
            report_text=_read_text(report_path),
        )

    @app.route("/project/<project_name>/plot/<plot_name>")
    def plot_file(project_name: str, plot_name: str):
        project_dir = _safe_project_dir(project_name)
        plot_path = project_dir / "plots" / plot_name
        if not plot_path.exists():
            abort(404)
        return send_file(plot_path)

    @app.route("/project/<project_name>/artifact")
    def artifact_view(project_name: str):
        project_dir = _safe_project_dir(project_name)
        relative_path = request.args.get("path", "")
        artifact_path = (project_dir / relative_path).resolve()
        if not str(artifact_path).startswith(str(project_dir.resolve())) or not artifact_path.exists():
            abort(404)
        if artifact_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
            return send_file(artifact_path)
        text = _read_text(artifact_path)
        return render_template(
            "artifact_view.html",
            project_name=project_name,
            artifact_path=artifact_path.relative_to(project_dir),
            artifact_text=text,
        )

    @app.route("/project/<project_name>/case-study/<case_id>")
    def case_study_view(project_name: str, case_id: str):
        project_dir = _safe_project_dir(project_name)
        case_dir = project_dir / "case_studies" / case_id
        if not case_dir.exists():
            abort(404)
        summary = _load_json(case_dir / "summary.json")
        tables = sorted(path.name for path in case_dir.glob("*.csv"))
        return render_template(
            "case_study.html",
            project_name=project_name,
            case_id=case_id,
            summary=summary,
            tables=tables,
        )

    @app.route("/project/<project_name>/upload-guide")
    def upload_guide(project_name: str):
        project_dir = _safe_project_dir(project_name)
        prediction_root = project_dir / "predictions"
        manifest_path = _first_existing(
            [
                project_dir / "manifests" / "manifest.csv",
                project_dir / "manifest.csv",
            ]
        )
        headers, rows = ([], [])
        if manifest_path:
            headers, rows = load_csv_preview(manifest_path, max_rows=12)
        return render_template(
            "upload_guide.html",
            project_name=project_name,
            prediction_root=prediction_root,
            manifest_path=manifest_path,
            headers=headers,
            rows=rows,
        )

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local HTML UI for the peptide-MHC analysis framework.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def discover_projects(outputs_root: Path) -> list[dict[str, object]]:
    if not outputs_root.exists():
        return []
    projects: list[dict[str, object]] = []
    for path in sorted(p for p in outputs_root.iterdir() if p.is_dir()):
        snapshot = _load_json(path / "analysis" / "analysis_snapshot.json")
        report_summary = _load_json(path / "analysis" / "report_summary.json")
        fallback_meta = derive_project_metadata(path)
        status = build_project_status(path, snapshot, report_summary)
        projects.append(
            {
                "name": path.name,
                "path": path,
                "num_variants": snapshot.get("num_variants") if snapshot else fallback_meta.get("num_variants"),
                "num_alleles": snapshot.get("num_alleles") if snapshot else fallback_meta.get("num_alleles"),
                "prediction_coverage": snapshot.get("prediction_coverage") if snapshot else fallback_meta.get("prediction_coverage"),
                "report_summary": report_summary,
                "status": status,
                "fallback_meta": fallback_meta,
            }
        )
    return projects


def discover_configs(examples_root: Path) -> list[Path]:
    if not examples_root.exists():
        return []
    return sorted(path for path in examples_root.glob("*.y*ml")) + sorted(path for path in examples_root.glob("*.json"))


def list_analysis_tables(project_dir: Path) -> list[dict[str, object]]:
    analysis_dir = project_dir / "analysis"
    manifests = _load_csv_rows(analysis_dir / "tables_manifest.csv")
    if manifests:
        return manifests
    tables = []
    for path in sorted(analysis_dir.glob("*.csv")):
        tables.append(
            {
                "table_id": path.stem,
                "source_path": str(path),
                "bundled_path": "",
                "title": path.stem.replace("_", " ").title(),
                "description": "Analysis table",
                "section": "analysis",
                "status": "ok",
                "notes": "",
            }
        )
    return tables


def list_plot_files(project_dir: Path) -> list[dict[str, object]]:
    plot_dir = project_dir / "plots"
    analysis_manifest = _load_csv_rows(project_dir / "analysis" / "figures_manifest.csv")
    if analysis_manifest:
        return analysis_manifest
    plots = []
    for path in sorted(plot_dir.glob("*.png")):
        plots.append(
            {
                "figure_id": path.stem,
                "source_path": str(path),
                "bundled_path": "",
                "title": path.stem.replace("_", " ").title(),
                "description": "Plot",
                "section": "plots",
                "status": "ok",
                "notes": "",
            }
        )
    return plots


def list_case_studies(project_dir: Path) -> list[dict[str, object]]:
    case_root = project_dir / "case_studies"
    if not case_root.exists():
        return []
    studies = []
    for case_dir in sorted(path for path in case_root.iterdir() if path.is_dir()):
        summary = _load_json(case_dir / "summary.json")
        studies.append(
            {
                "case_id": case_dir.name,
                "summary": summary,
            }
        )
    return studies


def build_project_status(project_dir: Path, snapshot: dict[str, object], report_summary: dict[str, object]) -> dict[str, str]:
    fallback_meta = derive_project_metadata(project_dir)
    prediction_coverage = int(snapshot.get("prediction_coverage", fallback_meta.get("prediction_coverage", 0)) or 0)
    structural_coverage = int(snapshot.get("structural_coverage", fallback_meta.get("structural_coverage", 0)) or 0)
    has_report = (project_dir / "analysis" / "report.md").exists()
    has_manifest = (project_dir / "manifests" / "manifest.csv").exists()
    if not has_manifest:
        has_manifest = (project_dir / "manifest.csv").exists()

    if structural_coverage > 0:
        return {"label": "Structural analysis available", "tone": "good"}
    if prediction_coverage > 0:
        return {"label": "Predictions found", "tone": "active"}
    if has_report:
        return {"label": "Inputs and reporting ready", "tone": "ready"}
    if has_manifest:
        return {"label": "Inputs only", "tone": "pending"}
    return {"label": "Sparse output", "tone": "quiet"}


def build_project_categories(
    project_dir: Path,
    tables: list[dict[str, object]],
    plots: list[dict[str, object]],
    case_studies: list[dict[str, object]],
    snapshot: dict[str, object],
    report_summary: dict[str, object],
) -> list[dict[str, object]]:
    categories: list[dict[str, object]] = []
    table_sections = _group_by_section(tables, "table")
    plot_sections = _group_by_section(plots, "figure")
    expected_sections = [
        "study_overview",
        "within_allele_analysis",
        "cross_allele_analysis",
        "pocket_signature_analysis",
        "hypothesis_generation",
    ]

    for section in expected_sections:
        section_tables = table_sections.get(section, [])
        section_plots = plot_sections.get(section, [])
        ok_tables = [item for item in section_tables if item.get("status") == "ok"]
        ok_plots = [item for item in section_plots if item.get("status") == "ok"]
        missing_plots = [item for item in section_plots if item.get("status") != "ok"]
        status = "empty"
        note = "No artifacts were detected for this section."
        if ok_tables or ok_plots:
            status = "available"
            note = "Artifacts are available for inspection."
        elif section_tables or section_plots:
            status = "partial"
            note = "This section is defined, but some selected artifacts are missing for the current run."
        categories.append(
            {
                "key": section,
                "label": SECTION_LABELS.get(section, section.replace("_", " ").title()),
                "status": status,
                "table_count": len(ok_tables),
                "plot_count": len(ok_plots),
                "missing_plot_count": len(missing_plots),
                "items": ok_tables[:3] + ok_plots[:3],
                "note": note,
            }
        )

    report_exists = (project_dir / "analysis" / "report.md").exists()
    categories.append(
        {
            "key": "reporting",
            "label": "Reporting",
            "status": "available" if report_exists else "empty",
            "table_count": 0,
            "plot_count": 0,
            "missing_plot_count": 0,
            "items": [],
            "note": "Markdown report and summary bundle are available." if report_exists else "No report was found.",
        }
    )

    categories.append(
        {
            "key": "case_studies",
            "label": "Case Studies",
            "status": "available" if case_studies else "empty",
            "table_count": len(case_studies),
            "plot_count": 0,
            "missing_plot_count": 0,
            "items": case_studies[:3],
            "note": "Filtered case-study views were generated." if case_studies else "No case-study outputs were found.",
        }
    )
    return categories


def _group_by_section(rows: list[dict[str, object]], item_kind: str) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        section = str(row.get("section") or ("analysis" if item_kind == "table" else "plots"))
        grouped.setdefault(section, []).append(row)
    return grouped


def derive_project_metadata(project_dir: Path) -> dict[str, int]:
    manifest_path = _first_existing(
        [
            project_dir / "manifests" / "manifest.csv",
            project_dir / "manifest.csv",
        ]
    )
    summary_path = _first_existing(
        [
            project_dir / "analysis" / "summary.csv",
            project_dir / "analysis" / "variant_summary.csv",
        ]
    )
    variants_path = project_dir / "colabfold_inputs" / "variants.csv"

    num_variants = None
    num_alleles = None
    prediction_coverage = 0
    structural_coverage = 0

    if manifest_path:
        rows = _load_csv_rows(manifest_path)
        if rows:
            num_variants = len(rows)
            allele_values = {
                row.get("allele_name")
                for row in rows
                if str(row.get("allele_name") or "").strip()
            }
            if allele_values:
                num_alleles = len(allele_values)

    if num_alleles is None and variants_path.exists():
        rows = _load_csv_rows(variants_path)
        allele_values = {
            row.get("allele_name")
            for row in rows
            if str(row.get("allele_name") or "").strip()
        }
        if allele_values:
            num_alleles = len(allele_values)
        if num_variants is None and rows:
            num_variants = len(rows)

    if summary_path:
        rows = _load_csv_rows(summary_path)
        if rows:
            if num_variants is None:
                num_variants = len(rows)
            if num_alleles is None:
                allele_values = {
                    row.get("allele_name")
                    for row in rows
                    if str(row.get("allele_name") or "").strip()
                }
                if allele_values:
                    num_alleles = len(allele_values)
            prediction_coverage = sum(
                1 for row in rows if str(row.get("prediction_present") or "").lower() == "true"
            )
            structural_coverage = sum(
                1
                for row in rows
                if str(row.get("total_peptide_mhc_contacts") or "").strip() not in {"", "NA", "nan"}
            )

    return {
        "num_variants": num_variants or 0,
        "num_alleles": num_alleles or 0,
        "prediction_coverage": prediction_coverage,
        "structural_coverage": structural_coverage,
    }


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def load_csv_preview(path: Path, max_rows: int = 200) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader, [])
        rows = []
        for index, row in enumerate(reader):
            if index >= max_rows:
                break
            rows.append(row)
    return headers, rows


def _read_project_name_from_config(config_path: Path) -> str:
    try:
        import yaml

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return str(payload.get("project_name") or config_path.stem)
    except Exception:
        return config_path.stem


def _resolve_project_dir(config_path: Path) -> Path | None:
    try:
        import yaml

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        output_dir = payload.get("output_dir")
        if not output_dir:
            return None
        resolved = Path(output_dir)
        if not resolved.is_absolute():
            resolved = (config_path.parent / resolved).resolve()
        return resolved
    except Exception:
        return None


def _safe_project_dir(project_name: str) -> Path:
    outputs_root = Path(current_app.config["OUTPUTS_ROOT"]).resolve()
    project_dir = (outputs_root / project_name).resolve()
    if not str(project_dir).startswith(str(outputs_root)) or not project_dir.exists():
        abort(404)
    return project_dir


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_csv_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def render_markdown_like(text: str) -> str:
    escaped = html.escape(text)
    lines = []
    for raw_line in escaped.splitlines():
        if raw_line.startswith("### "):
            lines.append(f"<h3>{raw_line[4:]}</h3>")
        elif raw_line.startswith("## "):
            lines.append(f"<h2>{raw_line[3:]}</h2>")
        elif raw_line.startswith("# "):
            lines.append(f"<h1>{raw_line[2:]}</h1>")
        elif raw_line.startswith("- "):
            lines.append(f"<li>{raw_line[2:]}</li>")
        elif raw_line.strip() == "":
            lines.append("<p></p>")
        else:
            lines.append(f"<p>{raw_line}</p>")
    html_text = "\n".join(lines)
    html_text = html_text.replace("<p></p>\n<li>", "<ul>\n<li>")
    html_text = html_text.replace("</li>\n<p></p>", "</li>\n</ul>\n<p></p>")
    if "<li>" in html_text and "</ul>" not in html_text:
        html_text += "\n</ul>"
    return html_text


def main() -> None:
    args = parse_args()
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
