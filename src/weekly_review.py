from __future__ import annotations

from pathlib import Path

from .review_packet import generate_project_review_packet, generate_workspace_review_packet
from .workspace import WorkspaceConfig


def generate_weekly_review(target: Path | WorkspaceConfig, is_workspace: bool = False, packet_id: str | None = None) -> Path:
    if is_workspace:
        return generate_workspace_review_packet(target, packet_id=packet_id)
    return generate_project_review_packet(Path(target), packet_id=packet_id)
