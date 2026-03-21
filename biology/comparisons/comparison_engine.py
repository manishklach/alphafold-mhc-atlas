from __future__ import annotations

from math import sqrt
from typing import Any


def compare_structures(wt_structure: dict[str, Any], mutant_structure: dict[str, Any]) -> dict[str, Any]:
    wt_residues = _index_residues(
        wt_structure.get("residues", []),
        wt_structure.get("coordinates", []),
    )
    mutant_residues = _index_residues(
        mutant_structure.get("residues", []),
        mutant_structure.get("coordinates", []),
    )

    residue_changes: list[dict[str, Any]] = []
    shifts: list[float] = []
    flags: list[str] = []

    all_keys = sorted(set(wt_residues) | set(mutant_residues))
    for key in all_keys:
        wt_residue = wt_residues.get(key)
        mutant_residue = mutant_residues.get(key)
        if wt_residue is None:
            residue_changes.append(
                {
                    "residue_id": mutant_residue["residue_id"],
                    "chain_id": key[0],
                    "residue_number": key[1],
                    "change_type": "present_in_mutant_only",
                    "wt_residue_name": None,
                    "mutant_residue_name": mutant_residue["residue_name"],
                }
            )
            continue
        if mutant_residue is None:
            residue_changes.append(
                {
                    "residue_id": wt_residue["residue_id"],
                    "chain_id": key[0],
                    "residue_number": key[1],
                    "change_type": "missing_in_mutant",
                    "wt_residue_name": wt_residue["residue_name"],
                    "mutant_residue_name": None,
                }
            )
            continue

        distance_shift = _distance_between_residues(wt_residue, mutant_residue)
        change_type = "matched"
        if wt_residue["residue_name"] != mutant_residue["residue_name"]:
            change_type = "mutated"
        elif distance_shift is not None and distance_shift > 0:
            change_type = "shifted"

        if distance_shift is not None:
            shifts.append(distance_shift)
        residue_changes.append(
            {
                "residue_id": wt_residue["residue_id"],
                "chain_id": key[0],
                "residue_number": key[1],
                "change_type": change_type,
                "wt_residue_name": wt_residue["residue_name"],
                "mutant_residue_name": mutant_residue["residue_name"],
                "shift": distance_shift,
            }
        )

    avg_shift = round(sum(shifts) / len(shifts), 4) if shifts else 0.0
    max_shift = round(max(shifts), 4) if shifts else 0.0
    large_shift_count = sum(1 for shift in shifts if shift > 2.0)
    confidence_delta = _confidence_delta(wt_structure, mutant_structure)

    if avg_shift > 2.0 or max_shift > 2.5:
        flags.append("high_structural_change")
    if confidence_delta < -5:
        flags.append("confidence_drop")

    result = {
        "residue_changes": residue_changes,
        "avg_shift": avg_shift,
        "max_shift": max_shift,
        "large_shift_count": large_shift_count,
        "confidence_delta": confidence_delta,
        "flags": sorted(set(flags)),
    }
    result["structure_shift_score"] = avg_shift
    return result


def _index_residues(
    residues: list[dict[str, Any]],
    coordinates: list[dict[str, Any]] | None = None,
) -> dict[tuple[str, int], dict[str, Any]]:
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    coordinate_index = {
        str(item.get("residue_id")): item
        for item in (coordinates or [])
        if item.get("residue_id") is not None
    }
    for residue in residues:
        chain_id = str(residue.get("chain_id") or "").strip()
        residue_number = int(residue.get("residue_number") or 0)
        if not chain_id or not residue_number:
            continue
        residue_record = dict(residue)
        coordinate_record = coordinate_index.get(str(residue.get("residue_id") or ""))
        if coordinate_record is not None:
            residue_record.setdefault("x", coordinate_record.get("x"))
            residue_record.setdefault("y", coordinate_record.get("y"))
            residue_record.setdefault("z", coordinate_record.get("z"))
        indexed[(chain_id, residue_number)] = residue_record
    return indexed


def _distance_between_residues(wt_residue: dict[str, Any], mutant_residue: dict[str, Any]) -> float | None:
    wt_center = _residue_point(wt_residue)
    mutant_center = _residue_point(mutant_residue)
    if wt_center is None or mutant_center is None:
        return None
    return round(
        sqrt(
            ((wt_center[0] - mutant_center[0]) ** 2)
            + ((wt_center[1] - mutant_center[1]) ** 2)
            + ((wt_center[2] - mutant_center[2]) ** 2)
        ),
        4,
    )


def _residue_point(residue: dict[str, Any]) -> tuple[float, float, float] | None:
    if {"x", "y", "z"} <= set(residue):
        try:
            return (float(residue["x"]), float(residue["y"]), float(residue["z"]))
        except (TypeError, ValueError):
            return None
    return _centroid(residue.get("coordinates", []))


def _centroid(coordinates: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    if not coordinates:
        return None
    total_x = 0.0
    total_y = 0.0
    total_z = 0.0
    count = 0
    for atom in coordinates:
        try:
            total_x += float(atom["x"])
            total_y += float(atom["y"])
            total_z += float(atom["z"])
        except (KeyError, TypeError, ValueError):
            continue
        count += 1
    if count == 0:
        return None
    return (total_x / count, total_y / count, total_z / count)


def _confidence_delta(wt_structure: dict[str, Any], mutant_structure: dict[str, Any]) -> float:
    wt_avg = wt_structure.get("confidence_summary", {}).get("avg")
    mutant_avg = mutant_structure.get("confidence_summary", {}).get("avg")
    if wt_avg is None or mutant_avg is None:
        return 0.0
    return round(float(mutant_avg) - float(wt_avg), 4)
