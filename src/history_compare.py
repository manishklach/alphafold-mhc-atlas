from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_access import safe_read_csv


def compare_history_tables(current_path: Path, previous_path: Path, key_columns: list[str]) -> pd.DataFrame:
    current_df = safe_read_csv(current_path)
    previous_df = safe_read_csv(previous_path)
    if current_df.empty and previous_df.empty:
        return pd.DataFrame()
    current_df = current_df.copy()
    previous_df = previous_df.copy()
    for column in key_columns:
        if column not in current_df.columns:
            current_df[column] = ""
        if column not in previous_df.columns:
            previous_df[column] = ""
    current_df["_state"] = "current"
    previous_df["_state"] = "previous"
    merged = current_df.merge(previous_df, on=key_columns, how="outer", indicator=True, suffixes=("_current", "_previous"))
    merged["change_type"] = merged["_merge"].map({"left_only": "new", "right_only": "dropped", "both": "retained"})
    return merged


def build_history_diff_summary(comparison_df: pd.DataFrame, label: str) -> str:
    lines = [f"# History Diff Summary: {label}", ""]
    if comparison_df.empty:
        lines.append("- No comparison data was available.")
        return "\n".join(lines)
    counts = comparison_df["change_type"].value_counts().to_dict()
    lines.append(f"- retained items: {counts.get('retained', 0)}")
    lines.append(f"- new items: {counts.get('new', 0)}")
    lines.append(f"- dropped items: {counts.get('dropped', 0)}")
    return "\n".join(lines)
