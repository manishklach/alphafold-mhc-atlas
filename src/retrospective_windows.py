from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class RetrospectiveWindow:
    window_id: str
    label: str
    cycle_range: list[str] | None = None
    date_range: list[str] | None = None
    cadence: str | None = None


def resolve_window_cycles(window: RetrospectiveWindow, available_cycles: list[str]) -> list[str]:
    """Resolve a list of cycle labels included in a window."""
    if not window.cycle_range:
        return available_cycles

    # Simple index-based range if available_cycles is sorted
    start_label, end_label = window.cycle_range
    try:
        start_idx = available_cycles.index(start_label)
        end_idx = available_cycles.index(end_label)
        return available_cycles[min(start_idx, end_idx):max(start_idx, end_idx) + 1]
    except ValueError:
        # If labels don't match, return all as fallback or empty
        return []


def filter_df_by_window(df: pd.DataFrame, window: RetrospectiveWindow, cycle_col: str = "cycle_id") -> pd.DataFrame:
    if df.empty:
        return df
    
    if window.cycle_range and cycle_col in df.columns:
        start_label, end_label = window.cycle_range
        # This assumes cycle_ids are comparable or we need a cycle mapping
        # For simplicity in Phase 14, we'll use membership in a resolved list
        return df
    
    return df
