from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd

from .scenario_playbooks import run_playbook
from .scenario_analysis import compare_scenarios


def compare_playbooks(
    workspace_dir: Path,
    playbook_id_a: str,
    playbook_id_b: str,
    tables: dict[str, pd.DataFrame],
    output_dir: Path | None = None
) -> dict[str, object]:
    output_dir = output_dir or workspace_dir / "playbook_comparisons" / f"{playbook_id_a}_vs_{playbook_id_b}_{datetime.now(timezone.utc).strftime('%Y%md%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    res_a = run_playbook(workspace_dir, playbook_id_a, tables, output_dir / playbook_id_a)
    res_b = run_playbook(workspace_dir, playbook_id_b, tables, output_dir / playbook_id_b)

    comp_res = compare_scenarios(res_a, res_b, output_dir)
    
    # Enrich with playbook comparison specific summary
    summary_path = output_dir / "playbook_comparison_summary.md"
    lines = [
        f"# Playbook Comparison: {playbook_id_a} vs {playbook_id_b}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Assumptions Difference",
        f"- **{playbook_id_a}**: {res_a['playbook']['description']}",
        f"- **{playbook_id_b}**: {res_b['playbook']['description']}",
        "",
        comp_res["summary_markdown"],
        "",
        "## Caveats",
        "Comparison surfaces how different analytical frames (playbooks) change prioritization. Disagreement between playbooks highlights variants sensitive to specific assumptions."
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    comp_res["playbook_comparison_summary.md"] = summary_path

    return comp_res
