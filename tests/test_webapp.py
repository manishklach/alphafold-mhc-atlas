import json

from src.webapp import create_app


def test_index_and_project_routes(tmp_path, monkeypatch) -> None:
    outputs_root = tmp_path / "outputs"
    examples_root = tmp_path / "examples"
    project_dir = outputs_root / "demo_project"
    analysis_dir = project_dir / "analysis"
    plots_dir = project_dir / "plots"
    analysis_dir.mkdir(parents=True)
    plots_dir.mkdir(parents=True)
    examples_root.mkdir(parents=True)
    (examples_root / "public_cross_allele_influenza_panel.yaml").write_text("project_name: demo\n", encoding="utf-8")

    (analysis_dir / "analysis_snapshot.json").write_text(
        json.dumps({"num_variants": 10, "num_alleles": 2, "prediction_coverage": 4}),
        encoding="utf-8",
    )
    (analysis_dir / "report_summary.json").write_text(
        json.dumps({"project_name": "demo_project", "hypothesis_count": 1}),
        encoding="utf-8",
    )
    (analysis_dir / "report.md").write_text("# Demo Report\n\n- item", encoding="utf-8")
    (analysis_dir / "summary.csv").write_text("variant_id,score\nv1,1.0\n", encoding="utf-8")
    (project_dir / "manifests").mkdir(exist_ok=True)
    (project_dir / "manifests" / "manifest.csv").write_text(
        "variant_id,allele_name\nv1,HLA-A*02:01\nv2,HLA-B*07:02\n",
        encoding="utf-8",
    )
    (analysis_dir / "figures_manifest.csv").write_text(
        "figure_id,source_path,bundled_path,title,description,section,status,notes\n"
        f"fig1,{plots_dir / 'coverage_overview.png'},,Coverage,desc,study_overview,ok,\n",
        encoding="utf-8",
    )
    (analysis_dir / "tables_manifest.csv").write_text(
        "table_id,source_path,bundled_path,title,description,section,status,notes\n"
        f"tab1,{analysis_dir / 'summary.csv'},,Summary,desc,analysis,ok,\n",
        encoding="utf-8",
    )
    (plots_dir / "coverage_overview.png").write_bytes(b"fakepng")

    app = create_app()
    app.config["TESTING"] = True
    monkeypatch.setitem(app.config, "OUTPUTS_ROOT", outputs_root)
    monkeypatch.setitem(app.config, "EXAMPLES_ROOT", examples_root)

    client = app.test_client()
    index_response = client.get("/")
    assert index_response.status_code == 200
    assert b"demo_project" in index_response.data
    assert b"Predictions found" in index_response.data
    assert b"public_cross_allele_influenza_panel.yaml" in index_response.data

    project_response = client.get("/project/demo_project")
    assert project_response.status_code == 200
    assert b"Demo Report" in project_response.data
    assert b"Analysis Categories" in project_response.data
    assert b"Reporting" in project_response.data

    table_response = client.get("/project/demo_project/table/summary.csv")
    assert table_response.status_code == 200
    assert b"variant_id" in table_response.data

    upload_response = client.get("/project/demo_project/upload-guide")
    assert upload_response.status_code == 200
    assert b"Where to place prediction folders" in upload_response.data
