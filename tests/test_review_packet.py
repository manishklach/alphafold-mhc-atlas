from pathlib import Path
import shutil

from src.decision_packet import generate_project_decision_packet, generate_workspace_decision_packet
from src.review_packet import generate_project_review_packet, generate_workspace_review_packet


def _copy_demo_project(tmp_path: Path) -> Path:
    source = Path("demo/pilot_review_demo/project")
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


def test_project_review_packet_generation(tmp_path: Path) -> None:
    project = _copy_demo_project(tmp_path)
    packet_dir = generate_project_review_packet(project, packet_id="weekly_demo")
    assert (packet_dir / "review_packet.md").exists()
    assert (packet_dir / "packet_manifest.csv").exists()
    assert "Conservative by design" in (packet_dir / "review_packet.md").read_text(encoding="utf-8")


def test_workspace_review_and_decision_packet_generation() -> None:
    review_dir = generate_workspace_review_packet("workspaces/demo_workspace.yaml", packet_id="workspace_demo")
    decision_dir = generate_workspace_decision_packet("workspaces/demo_workspace.yaml", packet_id="workspace_decision")
    assert (review_dir / "review_packet.md").exists()
    assert (decision_dir / "meeting_brief.md").exists()
    assert "Conservative by design" in (decision_dir / "meeting_brief.md").read_text(encoding="utf-8")
