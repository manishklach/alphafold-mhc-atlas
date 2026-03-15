from src.provenance import build_provenance


def test_build_provenance_handles_missing_requirements(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("output_dir: outputs/demo\nreference_peptide: GILGFVFTL\nmutation_positions: [1]\nallowed_amino_acids: [A]\nallele_name: HLA-A*02:01\n", encoding="utf-8")
    provenance = build_provenance(config_path, tmp_path / "missing_requirements.txt")
    assert provenance["config_digest"] != "missing"
    assert provenance["requirements_digest"] == "missing"
