from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import shutil

from .pilot_usage import summarize_usage
from .workflow_adoption import summarize_workflow_adoption
from .usage_friction import summarize_usage_friction
from .repeat_usage import summarize_repeat_usage
from .pilot_health import summarize_pilot_health
from .workspace import WorkspaceConfig, load_workspace_config


def build_product_learning_packet(
    workspace: WorkspaceConfig | str | Path,
    packet_id: str | None = None
) -> dict[str, Path]:
    config = load_workspace_config(workspace) if not isinstance(workspace, WorkspaceConfig) else workspace
    packet_id = packet_id or f"learning_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"
    
    output_dir = config.output_dir / "product_learning_packets" / packet_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Run all learning summaries
    usage = summarize_usage(config)
    adoption = summarize_workflow_adoption(config)
    friction = summarize_usage_friction(config)
    repeat = summarize_repeat_usage(config)
    health = summarize_pilot_health(config)
    
    # 2. Copy components to packet dir
    for results in [usage, adoption, friction, repeat, health]:
        for name, path in results.items():
            if path.exists() and not path.is_dir():
                shutil.copy(path, output_dir / name)

    # 3. Product Learning Summary
    summary_path = output_dir / "product_learning_summary.md"
    lines = [
        f"# Product Learning Summary: {config.name}",
        f"**Packet ID**: {packet_id}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Executive Learning",
        "This packet consolidates local usage patterns and workflow friction to inform future product development.",
        "",
        "### Key Findings",
        "- See `usage_digest.md` for event breakdown.",
        "- See `adoption_digest.md` for workflow stickiness.",
        "- See `friction_digest.md` for drop-off hotspots.",
        "- See `pilot_health_digest.md` for overall pilot status.",
        "",
        "## Caveats",
        "Learning artifacts are derived from local usage instrumentation. They reflect process adoption and friction, not market fit or scientific discovery quality."
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "product_learning_summary.md": summary_path,
        "packet_dir": output_dir
    }
