from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone
import json

from .data_access import safe_read_csv
from .org_retrospective import build_org_retrospective
from .system_health import build_org_system_health
from .capacity_retrospective import build_org_capacity_retrospective


def build_operating_review_packet(
    workspace_root: Path,
    output_root: Path,
    packet_id: str | None = None
) -> dict[str, Path]:
    packet_id = packet_id or f"org_review_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"
    packet_dir = output_root / "operating_review_packets" / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Components
    retro = build_org_retrospective(workspace_root, packet_dir)
    health = build_org_system_health(workspace_root, packet_dir)
    capacity = build_org_capacity_retrospective(workspace_root, packet_dir)

    # 2. Extract Key Status for Brief
    summary_path = packet_dir / "operating_summary.json"
    summary_data = {
        "packet_id": packet_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace_root)
    }
    summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    # 3. Create Operating Brief
    brief_path = packet_dir / "operating_review.md"
    lines = [
        f"# Operating Review: {packet_id}",
        "",
        "This packet aggregates decision and operational data across all active workspaces.",
        "",
        "## Included Artifacts",
        "- `org_retrospective_report.md`: High-level synthesis.",
        "- `health_digest.md`: Workflow and process stability.",
        "- `capacity_retrospective_digest.md`: Bandwidth and queue analysis.",
        "",
        "## Caveats",
        "Operating reviews provide portfolio-level visibility into discovery workflows. They are not intended for validating individual structural predictions."
    ]
    brief_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "operating_review.md": brief_path,
        "operating_summary.json": summary_path,
        "packet_dir": packet_dir
    }
