from pathlib import Path

from core.reporting.report_generator import generate_decision_report, generate_report


def test_generate_report_writes_markdown(tmp_path) -> None:
    output_path = tmp_path / "rankings.md"
    ranked_candidates = [
        {
            "candidate_id": "mutant_a",
            "priority_score": 2.5,
            "explanation": "Large structural shift with one residue mutation.",
            "flags": ["low_confidence"],
        },
        {
            "candidate_id": "mutant_b",
            "priority_score": 1.25,
            "explanation": "Moderate shift with no confidence issues.",
            "flags": [],
        },
    ]

    result = generate_report(ranked_candidates, output_path=output_path)

    assert result == output_path
    content = output_path.read_text(encoding="utf-8")
    assert "# Candidate Ranking Report" in content
    assert "### 1. mutant_a" in content
    assert "Priority score: 2.50" in content
    assert "Flags: low_confidence" in content
    assert "### 2. mutant_b" in content


def test_generate_decision_report_writes_candidate_report(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pipeline_output = {
        "candidate_id": "demo_candidate",
        "wt_structure": {"confidence_summary": {"avg": 85.7}},
        "mutant_structure": {"confidence_summary": {"avg": 71.0}},
        "comparison": {
            "avg_shift": 2.6,
            "max_shift": 3.1,
            "large_shift_count": 2,
            "confidence_delta": -14.7,
        },
        "ranking": {
            "priority_score": 6.0,
            "priority_label": "MEDIUM",
            "explanation": "Moderate structural change observed.",
            "flags": ["confidence_drop"],
        },
    }

    markdown = generate_decision_report(pipeline_output)
    report_path = Path("reports") / "demo_candidate.md"

    assert report_path.exists()
    assert "# MHC Atlas Decision Report" in markdown
    assert "- ID: demo_candidate" in markdown
    assert "- Priority Label: MEDIUM" in markdown
    assert "## Why this matters" in markdown
