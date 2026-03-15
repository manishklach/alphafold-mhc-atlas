from pathlib import Path

from src.app import load_scenario_templates
from src.data_access import safe_read_csv, safe_read_json, safe_read_text


def test_safe_read_helpers_and_template_loading(tmp_path) -> None:
    csv_path = tmp_path / "table.csv"
    json_path = tmp_path / "data.json"
    text_path = tmp_path / "note.md"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")
    json_path.write_text('{"x": 1}', encoding="utf-8")
    text_path.write_text("# note", encoding="utf-8")

    assert list(safe_read_csv(csv_path).columns) == ["a", "b"]
    assert safe_read_json(json_path)["x"] == 1
    assert "note" in safe_read_text(text_path)

    templates = load_scenario_templates(Path(__file__).resolve().parents[1] / "data" / "scenario_templates.yaml")
    assert any(template.scenario_id == "disruptive_shortlist" for template in templates)
