from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def preview_table(df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df.head(max_rows).copy()


def availability_summary(df: pd.DataFrame, key_columns: list[str]) -> dict[str, object]:
    if df.empty:
        return {"rows": 0, "available_columns": [], "missing_columns": key_columns}
    available = [column for column in key_columns if column in df.columns]
    missing = [column for column in key_columns if column not in df.columns]
    return {
        "rows": int(len(df)),
        "available_columns": available,
        "missing_columns": missing,
    }


def list_existing_files(root: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(sorted(root.glob(pattern)))
    return found
