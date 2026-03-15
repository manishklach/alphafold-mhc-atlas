import json
from pathlib import Path
import shutil

from src import cli


def test_cli_version(capsys) -> None:
    assert cli.main(["version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip()


def test_cli_validate_config(capsys) -> None:
    assert cli.main(["validate-config", "examples/sample_input.yaml"]) == 0
    captured = capsys.readouterr()
    assert "Valid config" in captured.out


def test_cli_inventory(capsys) -> None:
    assert cli.main(["inventory", "demo/cross_allele_demo/project"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["coverage"]["num_alleles"] == 2


def test_cli_check_environment(capsys) -> None:
    assert cli.main(["check-environment", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "mhc-atlas"


def test_cli_list_demos_and_walkthrough(capsys) -> None:
    assert cli.main(["list-demos"]) == 0
    listed = capsys.readouterr().out
    assert "golden_weekly_review_demo" in listed
    assert cli.main(["workflow-template", "list"]) == 0
    templates = capsys.readouterr().out
    assert "weekly_mutation_review" in templates
    assert cli.main(["demo-walkthrough", "golden_weekly_review_demo"]) == 0
    walkthrough = capsys.readouterr().out
    assert "Golden Weekly Review Demo" in walkthrough


def test_cli_review_and_feedback_commands(tmp_path: Path, capsys) -> None:
    source = Path("demo/cross_allele_demo/project")
    project = tmp_path / "project"
    shutil.copytree(source, project)
    assert cli.main(["review", "init", "--project", str(project), "--scenario", "disruptive_shortlist"]) == 0
    queue_path = Path(capsys.readouterr().out.strip())
    assert queue_path.exists()
    assert cli.main(
        [
            "feedback",
            "add",
            "--project",
            str(project),
            "--entity-type",
            "variant",
            "--entity-id",
            "demoA_pos2_A",
            "--comment",
            "Useful pilot note",
        ]
    ) == 0
    feedback_path = Path(capsys.readouterr().out.strip())
    assert feedback_path.exists()


def test_cli_handoff_and_checklist_commands(tmp_path: Path, capsys) -> None:
    source = Path("demo/cross_allele_demo/project")
    project = tmp_path / "project"
    shutil.copytree(source, project)
    assert cli.main(["checklist", "run", "--project", str(project), "--template", "pilot_handoff_review"]) == 0
    checklist_path = Path(capsys.readouterr().out.strip())
    assert checklist_path.exists()


def test_cli_workspace_and_packets(capsys) -> None:
    assert cli.main(["workspace", "inventory", "--workspace", "workspaces/demo_workspace.yaml"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"][0]["num_projects"] >= 2
    assert cli.main(["review-packet", "generate", "--workspace", "workspaces/demo_workspace.yaml", "--packet-id", "cli_demo"]) == 0
    review_path = Path(capsys.readouterr().out.strip())
    assert review_path.exists()
    assert cli.main(["decision-packet", "generate", "--workspace", "workspaces/demo_workspace.yaml", "--packet-id", "cli_decision"]) == 0
    decision_path = Path(capsys.readouterr().out.strip())
    assert decision_path.exists()


def test_cli_phase12_workspace_commands(tmp_path: Path, capsys) -> None:
    source = Path("demo/cross_allele_demo/project")
    project = tmp_path / "project"
    shutil.copytree(source, project)
    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        "\n".join(
            [
                "workspace:",
                "  workspace_id: ws_1",
                "  name: Test Workspace",
                "  description: Test",
                f"  output_dir: \"{(tmp_path / 'workspace_outputs').as_posix()}\"",
                "  projects:",
                "    - id: proj_a",
                f"      path: \"{project.as_posix()}\"",
            ]
        ),
        encoding="utf-8",
    )
    outcome_file = tmp_path / "outcomes.csv"
    outcome_file.write_text(
        "\n".join(
            [
                "outcome_id,entity_type,entity_id,project_id,workspace_id,cycle_id,outcome_class,outcome_source,outcome_timestamp,outcome_notes,linked_artifacts,reviewer_or_owner,confidence_in_outcome_context,not_model_truth_flag",
                "o1,shortlist_item,demoA_pos2_A,proj_a,ws_1,week_2,tested_followup,internal_review,2026-01-15T00:00:00+00:00,Example only,review/shortlist.csv,scientist,moderate,true",
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["outcomes", "import", "--workspace", str(workspace), "--file", str(outcome_file)]) == 0
    import_path = Path(capsys.readouterr().out.strip())
    assert import_path.exists()
    assert cli.main(["multicycle", "summarize", "--workspace", str(workspace)]) == 0
    multicycle_payload = json.loads(capsys.readouterr().out)
    assert "multicycle_decision_summary.csv" in multicycle_payload
    assert cli.main(["rationale", "summarize", "--workspace", str(workspace)]) == 0
    rationale_payload = json.loads(capsys.readouterr().out)
    assert "rationale_lineage.csv" in rationale_payload
    assert cli.main(["workflow-metrics", "summarize", "--workspace", str(workspace)]) == 0
    metrics_payload = json.loads(capsys.readouterr().out)
    assert "workflow_metrics.csv" in metrics_payload
    assert cli.main(["template-effectiveness", "summarize", "--workspace", str(workspace)]) == 0
    effectiveness_payload = json.loads(capsys.readouterr().out)
    assert "template_effectiveness_summary.csv" in effectiveness_payload
