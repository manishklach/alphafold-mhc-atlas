from __future__ import annotations

import gzip
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from .mutation_generator import VariantRecord


def parse_prediction_outputs(
    variants: list[VariantRecord],
    prediction_root: Path | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for variant in variants:
        variant_dir = prediction_root / variant.variant_id if prediction_root else None
        parsed = parse_variant_prediction_dir(variant.variant_id, variant_dir)
        parsed.update(
            {
                "variant_id": variant.variant_id,
                "local_variant_id": variant.local_variant_id,
                "peptide_id": variant.peptide_id,
                "allele_name": variant.allele_name,
                "wildtype_peptide": variant.wildtype_peptide,
                "mutant_peptide": variant.mutant_peptide,
                "mutated_position": variant.mutated_position,
                "wt_residue": variant.wt_residue,
                "mut_residue": variant.mut_residue,
                "is_wildtype": variant.is_wildtype,
            }
        )
        records.append(parsed)
    return records


def parse_variant_prediction_dir(variant_id: str, variant_dir: Path | None) -> dict[str, Any]:
    result = {
        "prediction_dir": str(variant_dir) if variant_dir else None,
        "prediction_present": False,
        "ranking_confidence": None,
        "mean_plddt": None,
        "pae_mean": None,
        "pae_min": None,
        "pae_max": None,
        "top_model_name": None,
        "structure_path": None,
        "best_available_confidence": None,
        "best_available_confidence_source": None,
        "notes": None,
    }

    if not variant_dir or not variant_dir.exists() or not variant_dir.is_dir():
        result["notes"] = "Prediction directory not found."
        return result

    result["prediction_present"] = True

    ranking_data = _load_ranking_debug(variant_dir / "ranking_debug.json")
    if ranking_data:
        result.update(ranking_data)

    best_model = result["top_model_name"]
    model_data = _load_model_payload(variant_dir, best_model)
    if model_data:
        result.update({key: value for key, value in model_data.items() if value is not None})

    pae_summary = _load_pae_summary(variant_dir, best_model)
    if pae_summary:
        result.update(pae_summary)

    structure_path = _find_structure_path(variant_dir, best_model)
    if structure_path:
        result["structure_path"] = str(structure_path)

    best_confidence, best_source = _pick_best_confidence(result)
    result["best_available_confidence"] = best_confidence
    result["best_available_confidence_source"] = best_source

    if result["prediction_present"] and not any(
        result[key] is not None for key in ["ranking_confidence", "mean_plddt", "pae_mean", "structure_path"]
    ):
        result["notes"] = "Prediction directory found, but no recognized confidence artifacts were parsed."

    return result


def _load_ranking_debug(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    order = payload.get("order") or []
    top_model_name = order[0] if order else None

    ranking_confidence = None
    confidence_map = payload.get("iptm+ptm") or payload.get("plddts") or payload.get("ptm")
    if isinstance(confidence_map, dict) and top_model_name in confidence_map:
        ranking_confidence = _to_float(confidence_map[top_model_name])

    return {
        "top_model_name": top_model_name,
        "ranking_confidence": ranking_confidence,
    }


def _load_model_payload(variant_dir: Path, best_model: str | None) -> dict[str, Any]:
    candidates = []
    if best_model:
        candidates.extend(
            [
                variant_dir / f"result_{best_model}.pkl",
                variant_dir / f"result_{best_model}.pkl.gz",
            ]
        )
    candidates.extend(sorted(variant_dir.glob("result_*.pkl")))
    candidates.extend(sorted(variant_dir.glob("result_*.pkl.gz")))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        payload = _read_pickle(candidate)
        if not isinstance(payload, dict):
            continue
        plddt = payload.get("plddt")
        if plddt is not None:
            mean_plddt = _safe_mean(plddt)
            return {"mean_plddt": mean_plddt}
    return {}


def _load_pae_summary(variant_dir: Path, best_model: str | None) -> dict[str, Any]:
    npz_candidates = []
    if best_model:
        npz_candidates.append(variant_dir / f"result_{best_model}.npz")
    npz_candidates.extend(sorted(variant_dir.glob("*.npz")))

    for candidate in npz_candidates:
        if not candidate.exists():
            continue
        try:
            with np.load(candidate) as data:
                pae = data.get("predicted_aligned_error")
                if pae is not None:
                    return _summarize_pae(pae)
        except Exception:
            continue

    json_candidates = []
    if best_model:
        json_candidates.append(variant_dir / f"{best_model}_pae.json")
        json_candidates.append(variant_dir / f"pae_{best_model}.json")
    json_candidates.extend(sorted(variant_dir.glob("*pae*.json")))

    for candidate in json_candidates:
        if not candidate.exists():
            continue
        pae_matrix = _read_pae_json(candidate)
        if pae_matrix is not None:
            return _summarize_pae(pae_matrix)

    return {}


def _find_structure_path(variant_dir: Path, best_model: str | None) -> Path | None:
    candidates: list[Path] = []
    if best_model:
        candidates.extend(
            [
                variant_dir / f"ranked_0.pdb",
                variant_dir / f"ranked_0.cif",
                variant_dir / f"ranked_0.mmcif",
                variant_dir / f"{best_model}.pdb",
                variant_dir / f"{best_model}.cif",
                variant_dir / f"{best_model}.mmcif",
            ]
        )
    candidates.extend(sorted(variant_dir.glob("ranked_*.pdb")))
    candidates.extend(sorted(variant_dir.glob("ranked_*.cif")))
    candidates.extend(sorted(variant_dir.glob("ranked_*.mmcif")))
    candidates.extend(sorted(variant_dir.glob("*.pdb")))
    candidates.extend(sorted(variant_dir.glob("*.cif")))
    candidates.extend(sorted(variant_dir.glob("*.mmcif")))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_pickle(path: Path) -> Any:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rb") as handle:
                return pickle.load(handle)
        with path.open("rb") as handle:
            return pickle.load(handle)
    except Exception:
        return None


def _read_pae_json(path: Path) -> np.ndarray | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if isinstance(payload, dict):
        if "predicted_aligned_error" in payload:
            payload = payload["predicted_aligned_error"]
        elif "pae" in payload:
            payload = payload["pae"]
        elif "distance" in payload:
            payload = payload["distance"]

    try:
        array = np.asarray(payload, dtype=float)
    except Exception:
        return None

    if array.ndim != 2:
        return None
    return array


def _summarize_pae(pae_matrix: Any) -> dict[str, float | None]:
    array = np.asarray(pae_matrix, dtype=float)
    if array.size == 0:
        return {"pae_mean": None, "pae_min": None, "pae_max": None}
    return {
        "pae_mean": float(np.nanmean(array)),
        "pae_min": float(np.nanmin(array)),
        "pae_max": float(np.nanmax(array)),
    }


def _safe_mean(values: Any) -> float | None:
    try:
        array = np.asarray(values, dtype=float)
    except Exception:
        return None
    if array.size == 0:
        return None
    return float(np.nanmean(array))


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_best_confidence(result: dict[str, Any]) -> tuple[float | None, str | None]:
    if result.get("ranking_confidence") is not None:
        return result["ranking_confidence"], "ranking_confidence"
    if result.get("mean_plddt") is not None:
        return result["mean_plddt"], "mean_plddt"
    return None, None
