import json

from src.parse_predictions import parse_variant_prediction_dir


def test_parse_variant_prediction_dir_handles_missing_directory(tmp_path) -> None:
    result = parse_variant_prediction_dir("WT", tmp_path / "missing")
    assert result["prediction_present"] is False
    assert result["ranking_confidence"] is None
    assert result["best_available_confidence"] is None


def test_parse_variant_prediction_dir_reads_ranking_and_structure(tmp_path) -> None:
    variant_dir = tmp_path / "pos2_ItoA"
    variant_dir.mkdir()
    (variant_dir / "ranking_debug.json").write_text(
        json.dumps({"order": ["model_1"], "iptm+ptm": {"model_1": 0.81}}),
        encoding="utf-8",
    )
    (variant_dir / "ranked_0.pdb").write_text("MODEL", encoding="utf-8")

    result = parse_variant_prediction_dir("pos2_ItoA", variant_dir)
    assert result["prediction_present"] is True
    assert result["top_model_name"] == "model_1"
    assert result["ranking_confidence"] == 0.81
    assert result["best_available_confidence"] == 0.81
    assert result["best_available_confidence_source"] == "ranking_confidence"
    assert result["structure_path"].endswith("ranked_0.pdb")
