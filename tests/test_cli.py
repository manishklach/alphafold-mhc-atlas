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
