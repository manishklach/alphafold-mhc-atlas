from src.demo_bundle import build_demo_bundle_manifest, validate_demo


def test_validate_demo_and_bundle_manifest(tmp_path) -> None:
    summary = validate_demo("small_project")
    assert summary["valid"] is True
    manifest_path = build_demo_bundle_manifest(tmp_path)
    assert manifest_path.exists()
    assert "small_project" in manifest_path.read_text(encoding="utf-8")
