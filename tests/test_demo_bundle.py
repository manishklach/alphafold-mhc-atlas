from src.demo_bundle import build_demo_bundle_manifest, validate_demo


def test_validate_demo_and_bundle_manifest(tmp_path) -> None:
    summary = validate_demo("small_project")
    assert summary["valid"] is True
    golden = validate_demo("golden_weekly_review_demo")
    assert golden["valid"] is True
    assert golden["demo_type"] == "workspace"
    manifest_path = build_demo_bundle_manifest(tmp_path)
    assert manifest_path.exists()
    assert "small_project" in manifest_path.read_text(encoding="utf-8")
    assert "golden_weekly_review_demo" in manifest_path.read_text(encoding="utf-8")
