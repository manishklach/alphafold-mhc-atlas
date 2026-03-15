import json

from src.project_index import build_project_inventory, write_project_inventory


def test_build_project_inventory_detects_available_modules(tmp_path) -> None:
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(parents=True)
    (analysis_dir / "summary.csv").write_text(
        "variant_id,allele_name,prediction_present,total_peptide_mhc_contacts\nv1,HLA-A*02:01,True,10\n",
        encoding="utf-8",
    )
    (analysis_dir / "variant_priority_table.csv").write_text(
        "variant_id,ranking_mode\nv1,disruptive_mutations\n",
        encoding="utf-8",
    )
    (analysis_dir / "optimized_mutation_panel.csv").write_text(
        "panel_id,variant_id\np1,v1\n",
        encoding="utf-8",
    )

    inventory = build_project_inventory(tmp_path)

    assert inventory["coverage"]["num_variants"] == 1
    assert "prioritization" in inventory["available_modules"]
    assert "panel_design" in inventory["available_modules"]

    inventory_path = write_project_inventory(tmp_path)
    assert json.loads(inventory_path.read_text(encoding="utf-8"))["project_name"] == tmp_path.name
