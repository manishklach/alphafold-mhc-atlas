from __future__ import annotations

from pathlib import Path
import pandas as pd

from .data_access import safe_read_csv


def select_retrospective_artifacts(workspace_dir: Path) -> dict[str, list[str]]:
    memory_dir = workspace_dir / "program_memory"
    
    selected_tables: list[str] = []
    selected_figures: list[str] = []

    potential_tables = [
        "multicycle_decision_summary.csv",
        "stable_shortlist_items.csv",
        "repeatedly_unresolved_items.csv",
        "outcomes_summary.csv",
        "outcome_aware_decision_summary.csv",
        "template_effectiveness_summary.csv",
        "workflow_metrics.csv",
        "execution_metrics.csv",
        "blocked_reasons_summary.csv",
        "pattern_synthesis.csv"
    ]

    for table in potential_tables:
        if (memory_dir / table).exists():
            selected_tables.append(table)

    #Figures/Plots from analysis folders across projects could be more complex.
    #For Phase 14 workspace retrospective, we focus on the memory dir tables.

    tables_df = pd.DataFrame([{"table_name": t, "path": str(memory_dir / t)} for t in selected_tables])
    tables_df.to_csv(memory_dir / "retrospective_selected_tables.csv", index=False)

    return {
        "selected_tables": selected_tables,
        "selected_figures": selected_figures
    }
