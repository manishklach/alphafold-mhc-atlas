from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .config import AMINO_ACIDS, AlleleSpec


@dataclass(frozen=True)
class ResolvedMHCSequences:
    allele_name: str
    class_type: str
    heavy_chain_sequence: str | None
    beta2m_sequence: str | None
    source: str
    resolved: bool
    metadata_only: bool
    notes: list[str]


def resolve_mhc_sequences(mhc_config: AlleleSpec) -> ResolvedMHCSequences:
    notes: list[str] = []

    explicit = _resolve_from_explicit_config(mhc_config)
    if explicit:
        return explicit

    if mhc_config.reference_file:
        reference_result = _resolve_from_reference_file(mhc_config)
        if reference_result:
            return reference_result
        notes.append(
            f"Allele '{mhc_config.allele_name}' was not resolved from reference file {mhc_config.reference_file}."
        )

    if mhc_config.allow_metadata_only_fallback:
        notes.append(
            "Proceeding in metadata-only fallback mode. Provide explicit sequences or populate the local reference file "
            "to generate true multichain FASTA inputs."
        )
        return ResolvedMHCSequences(
            allele_name=mhc_config.allele_name,
            class_type=mhc_config.class_type,
            heavy_chain_sequence=None,
            beta2m_sequence=None,
            source="metadata_only_fallback",
            resolved=False,
            metadata_only=True,
            notes=notes,
        )

    help_message = (
        f"Unable to resolve sequences for allele '{mhc_config.allele_name}'. "
        "Provide mhc.heavy_chain_sequence and mhc.beta2m_sequence explicitly, or add the allele to the local "
        "reference file and set mhc.reference_file."
    )
    if notes:
        help_message = f"{help_message} Details: {' '.join(notes)}"
    raise ValueError(help_message)


def _resolve_from_explicit_config(mhc_config: AlleleSpec) -> ResolvedMHCSequences | None:
    heavy = mhc_config.heavy_chain_sequence
    beta2m = mhc_config.beta2m_sequence
    if not heavy and not beta2m:
        return None
    if not heavy or not beta2m:
        raise ValueError(
            "Explicit sequence resolution requires both mhc.heavy_chain_sequence and mhc.beta2m_sequence "
            "for class I inputs."
        )
    _validate_sequence(heavy, "mhc.heavy_chain_sequence")
    _validate_sequence(beta2m, "mhc.beta2m_sequence")
    return ResolvedMHCSequences(
        allele_name=mhc_config.allele_name,
        class_type=mhc_config.class_type,
        heavy_chain_sequence=heavy,
        beta2m_sequence=beta2m,
        source="explicit_config",
        resolved=True,
        metadata_only=False,
        notes=[],
    )


def _resolve_from_reference_file(mhc_config: AlleleSpec) -> ResolvedMHCSequences | None:
    if not mhc_config.reference_file:
        return None
    entries = load_reference_entries(mhc_config.reference_file)
    entry = entries.get(mhc_config.allele_name)
    if not entry:
        return None

    class_type = str(entry.get("class_type") or mhc_config.class_type).strip().upper()
    heavy = _normalize_optional_sequence(entry.get("heavy_chain_sequence"))
    beta2m = _normalize_optional_sequence(entry.get("beta2m_sequence"))

    if class_type != "I":
        raise ValueError(
            f"Reference entry for allele '{mhc_config.allele_name}' specifies unsupported class_type '{class_type}'."
        )
    if not heavy or not beta2m:
        raise ValueError(
            f"Reference entry for allele '{mhc_config.allele_name}' is incomplete. Both heavy_chain_sequence and "
            "beta2m_sequence are required for class I inputs."
        )

    _validate_sequence(heavy, "reference heavy_chain_sequence")
    _validate_sequence(beta2m, "reference beta2m_sequence")
    return ResolvedMHCSequences(
        allele_name=mhc_config.allele_name,
        class_type=class_type,
        heavy_chain_sequence=heavy,
        beta2m_sequence=beta2m,
        source=f"reference_file:{mhc_config.reference_file}",
        resolved=True,
        metadata_only=False,
        notes=[],
    )


def load_reference_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Reference file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return _normalize_reference_payload(payload, path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_reference_payload(payload, path)
    if suffix == ".csv":
        return _load_reference_csv(path)
    raise ValueError(f"Unsupported reference file format: {path.suffix}")


def _normalize_reference_payload(payload: Any, path: Path) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError(f"Reference file {path} must deserialize to an object.")

    alleles = payload.get("alleles", payload)
    if not isinstance(alleles, dict):
        raise ValueError(f"Reference file {path} must contain an 'alleles' mapping or a top-level mapping.")

    normalized: dict[str, dict[str, Any]] = {}
    for allele_name, entry in alleles.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Reference entry for allele '{allele_name}' must be an object.")
        normalized[str(allele_name)] = entry
    return normalized


def _load_reference_csv(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"allele_name", "heavy_chain_sequence", "beta2m_sequence"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"Reference CSV {path} must contain columns: {sorted(required | {'class_type'})}"
            )
        entries: dict[str, dict[str, Any]] = {}
        for row in reader:
            allele_name = str(row["allele_name"]).strip()
            entries[allele_name] = {
                "class_type": row.get("class_type"),
                "heavy_chain_sequence": row.get("heavy_chain_sequence"),
                "beta2m_sequence": row.get("beta2m_sequence"),
            }
        return entries


def _normalize_optional_sequence(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value).strip().upper()


def _validate_sequence(sequence: str, field_name: str) -> None:
    invalid = sorted(set(sequence) - AMINO_ACIDS)
    if invalid:
        raise ValueError(f"{field_name} contains invalid amino acids: {invalid}")
