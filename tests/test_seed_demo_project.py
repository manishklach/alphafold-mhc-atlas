from pathlib import Path

from scripts.seed_demo_project import run_demo_pipeline


def test_run_demo_pipeline_creates_report() -> None:
    results = run_demo_pipeline()

    assert len(results["parsed_structures"]) == 3
    assert len(results["comparisons"]) == 2
    assert len(results["ranked_candidates"]) == 2

    report_path = Path(results["report_path"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Candidate Ranking Report" in content
    assert "mutant_a" in content
    assert "mutant_b" in content
